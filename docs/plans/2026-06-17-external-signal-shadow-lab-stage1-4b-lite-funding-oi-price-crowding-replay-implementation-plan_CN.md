# External Signal Shadow Lab Stage 1.4B-Lite Funding/OI/Price Crowding Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 基于已审计通过的 funding / OI / futures price 历史数据，实现一个 `crowding-only` 的 Stage 1.4B-Lite replay 管线，用来判断在不使用 liquidation 条件的前提下，这组 crowded-state label 是否仍保留最小可重复结构。

**Architecture:** 复用现有 `stage1_4a_funding.py`、`stage1_4a_oi.py`、`stage1_4a_price.py` 中已经验证过的数据字段与 as-of 语义，不复用 `stage1_3` 的候选定义，但复用其 replay / baseline / summary 结构思路。新增一套 `stage1_4b_lite_*` 模块，分别处理：候选事件定义、as-of 对齐、signed replay、matched random baseline、decision/summary 和中文 review。整个实现保持 `crowding-only falsification` 定位，不宣称 full composite，不给 paper/live 结论。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、现有 `src/research/external_signal_shadow/stage1_4a_*` 模块、pytest、ruff、JSON/JSONL。

---

## 0. 执行前边界

本计划只实现：

```text
funding_oi_price_crowding_replay_only
```

禁止实现：

```text
liquidation trigger
full derivatives stress composite
paper trading enablement
live trading enablement
strategy ready / alpha approved
post-hoc threshold tuning
multiple detection-window search
```

必须在 summary 顶层固定写出：

```json
{
  "liquidation_used": false,
  "full_derivatives_stress_composite_claim_allowed": false,
  "stage1_4b_full_composite_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "signed_replay_only": true,
  "execution_intent_allowed": false,
  "b_lite_failure_interpretation": "crowding_only_failed_not_full_composite_failed",
  "liquidation_missing_leg_remains_unresolved": true
}
```

补充说明：

- `B-Lite fail != full composite fail`
- `B-Lite pass != strategy ready`
- `oi_contraction_after_price_flush` 必须标记为 `deleveraging_proxy_only = true`，不能写成 liquidation 事件。
- 所有验证命令统一使用 `PYTHONPATH=src:.`。
- 本计划不包含任何自动 `git commit`。每个任务结束后最多执行 `git status --short`，由用户决定是否提交。

---

## 1. 文件结构

### 新增文件

- `src/research/external_signal_shadow/stage1_4b_lite_models.py`
- `src/research/external_signal_shadow/stage1_4b_lite_loader.py`
- `src/research/external_signal_shadow/stage1_4b_lite_signals.py`
- `src/research/external_signal_shadow/stage1_4b_lite_replay.py`
- `src/research/external_signal_shadow/stage1_4b_lite_baseline.py`
- `src/research/external_signal_shadow/stage1_4b_lite_summary.py`
- `scripts/external_signal_shadow/run_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- `scripts/external_signal_shadow/review_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_config.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_models.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_loader.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_replay.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_baseline.py`
- `tests/research/external_signal_shadow/test_stage1_4b_lite_summary.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- `tests/fixtures/external_signal_shadow/stage1_4b_lite_funding_rows.json`
- `tests/fixtures/external_signal_shadow/stage1_4b_lite_oi_rows.json`
- `tests/fixtures/external_signal_shadow/stage1_4b_lite_price_rows.json`

### 修改文件

- `configs/base.py`
- `src/research/external_signal_shadow/stage1_4a_funding.py` 仅在必要时复用/暴露 helper；否则不改
- `src/research/external_signal_shadow/stage1_4a_oi.py` 仅在必要时复用/暴露 helper；否则不改
- `src/research/external_signal_shadow/stage1_4a_price.py` 仅在必要时复用/暴露 helper；否则不改

### 设计原则

- 新增模块，不把 B-Lite 混进 `stage1_4a_orchestrator.py` 或 `stage1_3_orchestrator.py`。
- 候选定义、replay、baseline、summary、review 独立，便于逐块测试。
- 默认只支持一个预注册参数组：`4h detection + 15m entry + 4h primary forward`。
- 任何 threshold 必须来自 `configs/base.py`，不得在 `src/` 中散落 magic number。
- `funding percentile` 固定采用 `symbol-specific rolling 90d, no-lookahead`，不采用全局静态分位数。

---

## 2. Task 1: 配置常量、阈值、顶层枚举

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_config.py`

### Step 1: 写失败测试

至少覆盖：

```python
from configs import base


def test_stage1_4b_lite_threshold_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_DETECTION_WINDOW_HOURS == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_ENTRY_DELAY_BARS == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRIMARY_FORWARD_WINDOW_HOURS == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_SECONDARY_FORWARD_WINDOWS_HOURS == (1, 12)

    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE == 90
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PERCENTILE_LOOKBACK_DAYS == 90
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_FUNDING_HISTORY_POINTS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT == 0.02
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT == -0.02
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT == 0.015
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT == 0.02
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_BASELINE_1H_RETURN_PCT == 0.015

    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PUBLISH_LAG_MS == base.EXTERNAL_SIGNAL_STAGE1_4_FUNDING_PUBLISH_LAG_MS
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_OI_STALENESS_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_OI_HISTORY_POINTS >= 2
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_COOLDOWN_HOURS == 4

    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_RANDOM_BASELINE_TRIALS >= 500
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_COST_SCENARIOS_BPS == (30, 50, 80)
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_COUNT == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_SYMBOL_EVENT_SHARE == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_DAY_EVENT_SHARE == 0.20
    assert base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE == 0.30
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_config.py -q
```

### Step 3: 实现最小配置

在 `configs/base.py` 新增：

```python
EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_DETECTION_WINDOW_HOURS = 4
EXTERNAL_SIGNAL_STAGE1_4B_LITE_ENTRY_DELAY_BARS = 1
EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRIMARY_FORWARD_WINDOW_HOURS = 4
EXTERNAL_SIGNAL_STAGE1_4B_LITE_SECONDARY_FORWARD_WINDOWS_HOURS = (1, 12)

EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE = 90
EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PERCENTILE_LOOKBACK_DAYS = 90
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_FUNDING_HISTORY_POINTS = 30
EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT = 0.02
EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT = -0.02
EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT = 0.015
EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT = 0.02
EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_BASELINE_1H_RETURN_PCT = 0.015

EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PUBLISH_LAG_MS = EXTERNAL_SIGNAL_STAGE1_4_FUNDING_PUBLISH_LAG_MS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_OI_STALENESS_MS = 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_OI_HISTORY_POINTS = 2
EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_COOLDOWN_HOURS = 4

EXTERNAL_SIGNAL_STAGE1_4B_LITE_RANDOM_BASELINE_TRIALS = 500
EXTERNAL_SIGNAL_STAGE1_4B_LITE_COST_SCENARIOS_BPS = (30, 50, 80)
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_COUNT = 100
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_DAYS = 20
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.50
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_DAY_EVENT_SHARE = 0.20
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE = 0.30
```

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_config.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 3. Task 2: 数据 loader、JSON/JSONL 支持与 schema normalization

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4b_lite_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_loader.py`

### Step 1: 写失败测试

至少覆盖：

- `.json` list root 支持
- `.jsonl` one object per line 支持
- funding schema normalization:
  - `symbol, fundingTime, fundingRate`
- OI schema normalization:
  - `symbol, timestamp / timestamp_ms, sumOpenInterest / openInterest`
- price schema normalization:
  - `symbol, bar_start_ms/open_time, open/high/low/close, quote_volume`

示例：

```python
from research.external_signal_shadow.stage1_4b_lite_loader import (
    load_funding_rows,
    load_oi_rows,
    load_price_rows,
)


def test_runner_loads_json_and_jsonl_inputs(tmp_path):
    ...


def test_price_loader_normalizes_bar_fields():
    rows = load_price_rows("tests/fixtures/external_signal_shadow/stage1_4b_lite_price_rows.json")
    assert rows[0]["bar_start_ms"] > 0
    assert rows[0]["close_price"] > 0
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_loader.py -q
```

### Step 3: 实现 loader

实现至少：

```python
load_funding_rows(path: str) -> list[dict]
load_oi_rows(path: str) -> list[dict]
load_price_rows(path: str) -> list[dict]
```

要求：

- 支持 `.json` 根对象为 `list[dict]`
- 支持 `.jsonl` 一行一个对象
- normalization 只发生在 loader，不把临时字段分支塞进 replay 核心逻辑
- 不可识别的字段必须抛出结构化错误，不能静默跳过

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_loader.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 4. Task 3: 数据模型与预注册候选定义

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4b_lite_models.py`
- Create: `src/research/external_signal_shadow/stage1_4b_lite_signals.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py`

### Step 1: 写失败测试

至少覆盖：

- `candidate family` 固定只有 3 个
- `event_detection_window = 4h`
- `signed_replay_only = true`
- `oi_contraction_after_price_flush` 标记为 `deleveraging_proxy_only = true`
- `positive funding extreme = long crowded`
- `negative funding extreme = short crowded`

示例：

```python
from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent
from research.external_signal_shadow.stage1_4b_lite_signals import build_candidate_definitions


def test_build_candidate_definitions_freezes_three_families():
    defs = build_candidate_definitions()
    assert set(defs) == {
        "oi_expansion_trend_confirmation",
        "funding_oi_crowding_unwind",
        "oi_contraction_after_price_flush",
    }
    assert defs["oi_contraction_after_price_flush"]["deleveraging_proxy_only"] is True
    assert defs["funding_oi_crowding_unwind"]["signed_replay_only"] is True
    assert defs["oi_expansion_trend_confirmation"]["long"]["price_4h_return_gte"] == 0.015
    assert defs["funding_oi_crowding_unwind"]["long_crowded_unwind"]["signed_direction"] == -1
    assert defs["oi_contraction_after_price_flush"]["down_flush"]["liquidation_observed"] is False


def test_candidate_event_requires_signed_direction_and_entry_bar():
    event = CandidateEvent(
        candidate_name="funding_oi_crowding_unwind",
        symbol="BTCUSDT",
        event_time_ms=1,
        event_available_at_ms=2,
        entry_bar_start_ms=3,
        signed_direction=1,
        metadata={"crowded_side": "short"},
    )
    assert event.signed_direction == 1
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_models.py tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 3: 实现 dataclass 与候选定义注册表

在 `stage1_4b_lite_models.py` 定义至少：

```python
@dataclass(frozen=True)
class CandidateEvent:
    candidate_name: str
    symbol: str
    event_time_ms: int
    event_available_at_ms: int
    entry_bar_start_ms: int
    signed_direction: int  # +1 long diagnostic, -1 short diagnostic
    metadata: dict[str, Any]
```

在 `stage1_4b_lite_signals.py` 定义：

- `build_candidate_definitions() -> dict[str, dict[str, Any]]`
- `compute_event_available_at_ms(...)`
- `compute_price_4h_return_pct(...)`
- `compute_oi_4h_change_pct(...)`
- `funding_percentile_label(...)`

必须将 design 中冻结的三组定义编码为单一参数组，不允许在接口中暴露任意 `window_hours` 输入。

必须显式冻结以下公式：

```text
oi_expansion_trend_confirmation
  long:
    price_4h_return_pct >= +1.5%
    oi_4h_change_pct >= +2.0%
    funding_abs_percentile < 90
    signed_direction = +1
  short diagnostic:
    price_4h_return_pct <= -1.5%
    oi_4h_change_pct >= +2.0%
    funding_abs_percentile < 90
    signed_direction = -1

funding_oi_crowding_unwind
  long-crowded unwind:
    funding_percentile >= 90
    oi_4h_change_pct <= -2.0%
    price_4h_return_pct <= -1.0%
    signed_direction = -1
    crowded_side = long
  short-crowded unwind:
    funding_percentile <= 10
    oi_4h_change_pct <= -2.0%
    price_4h_return_pct >= +1.0%
    signed_direction = +1
    crowded_side = short

oi_contraction_after_price_flush
  down flush:
    price_4h_return_pct <= -2.0%
    oi_4h_change_pct <= -2.0%
    signed_direction = +1
    deleveraging_proxy_only = true
    liquidation_observed = false
  up squeeze:
    price_4h_return_pct >= +2.0%
    oi_4h_change_pct <= -2.0%
    signed_direction = -1
    deleveraging_proxy_only = true
    liquidation_observed = false
```

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_models.py tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 5. Task 4: funding percentile、funding / OI / price as-of 对齐 helper

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_4a_funding.py` 仅在必要时增加 helper；否则在 B-Lite 模块内部实现 wrapper
- Modify: `src/research/external_signal_shadow/stage1_4a_oi.py` 仅在必要时增加 helper；否则在 B-Lite 模块内部实现 wrapper
- Modify: `src/research/external_signal_shadow/stage1_4a_price.py` 仅在必要时增加 helper；否则在 B-Lite 模块内部实现 wrapper
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py`

### Step 1: 写失败测试

至少覆盖：

- funding percentile 使用 `symbol-specific rolling 90d`，且只能看事件前历史
- funding 必须取 `latest fundingTime <= event_available_at_ms - funding_publish_lag_ms`
- OI 必须取 `latest row <= event_available_at_ms` 和 `latest row <= event_available_at_ms - 4h`
- OI stale 超限时事件无效
- price 必须用 futures price，entry 取第一根可交易 15m bar
- 4h price return 严格按 `16` 根 15m bars 计算
- 4h OI change 对于 1h OI 严格按 `4h` 差值计算，不允许 lookahead

示例：

```python
def test_funding_percentile_uses_symbol_specific_past_window_only():
    ...


def test_funding_state_uses_latest_record_before_event_minus_publish_lag():
    rows = [
        {"symbol": "BTCUSDT", "fundingTime": 1_000, "fundingRate": "0.0001"},
        {"symbol": "BTCUSDT", "fundingTime": 2_000, "fundingRate": "0.0002"},
    ]
    state = funding_state_at_event(rows, event_available_at_ms=7_000, funding_publish_lag_ms=15 * 60 * 1000)
    assert state["fundingTime"] == 2_000


def test_oi_change_uses_asof_event_and_asof_event_minus_4h_without_lookahead():
    ...
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 3: 实现 helper/wrapper

实现至少以下语义：

```python
funding_state_at_event(rows, event_available_at_ms, funding_publish_lag_ms)
funding_percentile_at_event(rows, event_available_at_ms, funding_publish_lag_ms)
oi_state_at_or_before(rows, target_ms, max_staleness_ms)
price_bar_at_or_after_event(bars, event_available_at_ms, entry_delay_bars)
```

要求：

- `funding_percentile_at_event` 固定采用：
  - symbol-specific rolling history
  - lookback = 90d
  - only `fundingTime <= event_available_at_ms - funding_publish_lag_ms`
  - `min_history_points >= 30`
  - 排除 future rows
- funding 不得使用未来 settlement row
- OI 需要 `min_oi_history_points` 和 `max_oi_staleness_ms` 双重保护
- `compute_price_4h_return_pct` 必须基于 `16` 根 15m bars
- `compute_oi_4h_change_pct` 必须使用 `event_available_at_ms` 与 `event_available_at_ms - 4h` 的 as-of 值
- price 必须优先 futures price，不允许默认退回 spot 除非调用方显式标记 proxy

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 6. Task 5: 候选事件扫描器与 cooldown 去重

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_4b_lite_signals.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py`
- Fixtures: `tests/fixtures/external_signal_shadow/stage1_4b_lite_funding_rows.json`, `...oi_rows.json`, `...price_rows.json`

### Step 1: 写失败测试

至少覆盖三类事件：

- `oi_expansion_trend_confirmation` long trigger
- `funding_oi_crowding_unwind` short crowded unwind => signed long
- `oi_contraction_after_price_flush` down flush => rebound long
- same symbol + candidate + signed_direction within 4h only keep first event

示例：

```python
def test_detect_oi_expansion_trend_confirmation_long_event():
    events = detect_candidate_events(...)
    assert len(events) == 1
    assert events[0].candidate_name == "oi_expansion_trend_confirmation"
    assert events[0].signed_direction == 1


def test_detect_funding_oi_crowding_unwind_short_crowded_unwind_event():
    events = detect_candidate_events(...)
    assert events[0].metadata["crowded_side"] == "short"
    assert events[0].signed_direction == 1


def test_oi_contraction_after_price_flush_marks_deleveraging_proxy_only():
    events = detect_candidate_events(...)
    assert events[0].metadata["deleveraging_proxy_only"] is True
    assert events[0].metadata["liquidation_observed"] is False


def test_event_cooldown_prevents_repeated_overlapping_events():
    events = detect_candidate_events(...)
    assert len(events) == 1
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 3: 实现 `detect_candidate_events(...)`

接口建议：

```python
def detect_candidate_events(
    *,
    symbol: str,
    funding_rows: list[dict],
    oi_rows: list[dict],
    price_bars: list[HistoricalBar],
) -> list[CandidateEvent]:
    ...
```

必须要求：

- 只按预注册定义检测三类候选
- 不允许调用方传入任意 threshold / 任意 `window_hours`
- 同一 `symbol + candidate_name + event_time_ms` 不重复发事件
- 同一 `symbol + candidate_name + signed_direction` 在 `4h cooldown` 内只保留第一个事件
- 对于 short diagnostic 事件，必须保留 `signed_direction = -1`，但 summary/review 必须说明仅用于 signed replay，不代表 live short intent

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 7. Task 6: signed replay 与 forward metric

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4b_lite_replay.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_replay.py`

### Step 1: 写失败测试

至少覆盖：

- `entry_delay_bars >= 1`
- primary 4h terminal return after cost
- secondary 1h / 12h report-only
- short diagnostic 用 signed return
- forward window 不完整时跳过事件
- short replay summary fields set `short_execution_intent_allowed = false`

示例：

```python
def test_replay_event_computes_signed_terminal_return_after_cost():
    result = replay_event(...)
    assert result["terminal_return_4h_net_bps_after_50bps"] == expected


def test_replay_skips_event_when_forward_window_incomplete():
    assert replay_event(...) is None
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_replay.py -q
```

### Step 3: 实现最小 replay

实现至少：

```python
replay_event(...)
replay_candidate_events(...)
```

要求：

- primary metric 固定为：
  - `terminal_return_4h_net_bps_after_50bps_median`
- secondary windows 只报告，不参与 pass/fail
- `cost_scenarios_bps = (30, 50, 80)` 都要算
- signed replay 规则：
  - `signed_direction = +1` => long return
  - `signed_direction = -1` => short-style signed return
- replay 输出必须带：
  - `signed_short_replay_present`
  - `short_execution_intent_allowed = false`
  - `borrow_or_margin_feasibility_checked = false`

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_replay.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 8. Task 7: matched random baseline 与 price_move_1h baseline

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4b_lite_baseline.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_baseline.py`

### Step 1: 写失败测试

至少覆盖：

- `random_baseline_trials >= 500`
- event count match
- symbol distribution match
- hour-of-day exact match, fallback ±1h
- exclude candidate timestamps
- incomplete forward window not allowed
- sampling failure count output
- `price_move_1h baseline` 触发与计算

示例：

```python
def test_random_baseline_matches_event_count_and_symbol_distribution():
    baseline = sample_random_baseline(...)
    assert baseline["sampled_event_count"] == 4
    assert baseline["symbol_distribution"] == {"BTCUSDT": 2, "ETHUSDT": 2}


def test_random_baseline_reports_insufficient_sampling_when_hour_match_unavailable():
    baseline = sample_random_baseline(...)
    assert baseline["baseline_sampling_insufficient"] is True
    assert baseline["baseline_sampling_failure_count"] > 0


def test_price_move_1h_baseline_is_computed_and_required():
    baseline = compute_price_move_1h_baseline(...)
    assert baseline["baseline_name"] == "price_move_1h"
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_baseline.py -q
```

### Step 3: 实现 baseline sampler

实现至少：

```python
build_candidate_population(...)
sample_symbol_hour_matched_random_baseline(...)
compute_random_baseline_summary(...)
compute_price_move_1h_baseline(...)
```

要求：

- 使用固定 `random_seed`
- 每个 trial 的 event_count 与候选完全一致
- symbol distribution 完全匹配
- hour-of-day 尽量精确匹配，不能精确匹配时允许 ±1h
- 必须排除 candidate 自身 timestamp
- 必须输出：
  - `baseline_sampling_failure_count`
  - `baseline_sampling_insufficient`
- `price_move_1h baseline` 规则固定为：
  - `abs(price_1h_return) >= EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_BASELINE_1H_RETURN_PCT`
  - `signed_direction = sign(price_1h_return)`
  - 使用相同 replay / cost / concentration 口径

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_baseline.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 9. Task 8: summary decision engine、candidate-level / overall-level decision 与 concentration gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4b_lite_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4b_lite_summary.py`

### Step 1: 写失败测试

至少覆盖：

- `crowding_lite_promising`
- `crowding_lite_weak`
- `crowding_lite_failed`
- `top_5_positive_events_gross_profit_share`
- `max_single_symbol_event_share`
- `max_single_day_event_share`
- `B-Lite fail != full composite fail`
- overall-level promising / weak / failed 分离

示例：

```python
def test_summary_failed_when_no_positive_baseline_excess():
    summary = decide_stage1_4b_lite_summary({...})
    assert summary["decision"] == "crowding_lite_failed"
    assert summary["primary_blocker"] == "no_positive_baseline_excess"
    assert summary["b_lite_failure_interpretation"] == "crowding_only_failed_not_full_composite_failed"


def test_summary_weak_when_density_passes_but_median_net_return_not_positive():
    summary = decide_stage1_4b_lite_summary({...})
    assert summary["decision"] == "crowding_lite_weak"


def test_overall_promising_requires_at_least_one_candidate_promising():
    summary = decide_stage1_4b_lite_summary({...})
    assert summary["decision"] == "crowding_lite_promising"
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_summary.py -q
```

### Step 3: 实现 summary builder

实现至少：

```python
def compute_concentration_stats(events, replay_rows) -> dict: ...
def decide_candidate_family_summary(result: dict) -> dict: ...
def decide_stage1_4b_lite_summary(summary: dict) -> dict: ...
```

要求：

- `top_5_positive_events_gross_profit_share` 只以正毛利事件为分母
- 同时输出：
  - `top_5_abs_pnl_share`
- `crowding_lite_failed` 不得被解释成 full composite failed
- 顶层 summary 必须保留 design 中全部安全字段
- 顶层 gate 必须显式检查：
  - `must_beat_price_move_1h_baseline = true`
  - `must_beat_symbol_hour_matched_random_baseline = true`
- 顶层 decision 规则必须固定：
  - `overall promising`:
    - at least one candidate family promising
    - and no safety violation
  - `overall weak`:
    - no promising
    - but at least one candidate density_pass / diagnostic_positive
  - `overall failed`:
    - all candidate families failed or data insufficient
- candidate-level blocker 必须保留，不能只保留 overall blocker
- `next_action` 必须是有限枚举，例如：
  - `stop_crowding_only_branch`
  - `keep_as_secondary_track_only`
  - `prepare_stage1_4c_joint_decision_review`

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4b_lite_summary.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 10. Task 9: runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4b_lite_funding_oi_price_crowding_replay.py`

### Step 1: 写失败测试

至少覆盖：

- 接收 funding / OI / price 输入路径
- 支持 fixture 模式
- 支持 `.json` 与 `.jsonl` 输入
- 写出 summary JSON
- 不传 liquidation 输入
- 顶层安全字段为 false

示例：

```python
def test_runner_writes_b_lite_summary(tmp_path):
    summary_path = tmp_path / "summary.json"
    rc = main([
        "--funding-input", "tests/fixtures/...funding_rows.json",
        "--oi-input", "tests/fixtures/...oi_rows.json",
        "--price-input", "tests/fixtures/...price_rows.json",
        "--output-summary", str(summary_path),
        "--fixture-run",
    ])
    assert rc == 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["liquidation_used"] is False
    assert summary["signed_replay_only"] is True
    assert summary["research_result_valid"] is False
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4b_lite_funding_oi_price_crowding_replay.py -q
```

### Step 3: 实现 CLI

参数至少包括：

```text
--funding-input PATH
--oi-input PATH
--price-input PATH
--output-summary PATH
--fixture-run
```

要求：

- runner 内完成：loader -> 扫描候选 -> replay -> baseline -> summary
- 默认 universe 先固定 `BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT`
- 若数据不足，返回 `crowding_lite_failed` 或 `crowding_lite_weak`，但不得抛出与边界无关的异常
- `fixture_run = true` 时必须写：
  - `research_result_valid = false`
- 真实运行才允许：
  - `fixture_run = false`
  - `research_result_valid = true`

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4b_lite_funding_oi_price_crowding_replay.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 11. Task 10: 中文 review script

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_4b_lite_funding_oi_price_crowding_replay.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_4b_lite_funding_oi_price_crowding_replay.py`

### Step 1: 写失败测试

至少覆盖：

- review 输出每个 candidate family 的 gate、density、baseline、blocker
- 强制写出 `B-Lite fail != full composite fail`
- 强制写出 `liquidation_missing_leg_remains_unresolved = true`
- 强制写出 short replay 不是 live short intent

示例：

```python
def test_review_marks_b_lite_as_crowding_only_not_full_composite(tmp_path):
    ...
    text = review_path.read_text(encoding="utf-8")
    assert "crowding-only replay" in text
    assert "B-Lite fail != full composite fail" in text
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4b_lite_funding_oi_price_crowding_replay.py -q
```

### Step 3: 实现 review script

必须输出：

- 顶层 decision / next_action
- 每个 candidate family：
  - event_count
  - event_days
  - symbols_with_events
  - median_net_return_after_50bps
  - baseline_excess_net_bps
  - left_tail_vs_baseline
  - top_5_positive_events_gross_profit_share
  - blocker
- 顶层解释：
  - `B-Lite` 是 crowding-only precheck
  - 不能替代 liquidation composite
  - 失败不能解释成 full composite fail
  - `signed short replay` 只用于 diagnostic，不代表可执行 short 策略

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4b_lite_funding_oi_price_crowding_replay.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 12. Task 11: 端到端 fixture smoke + 最小真实运行说明

**Files:**
- Use existing scripts/modules only
- Optional fixtures under `tests/fixtures/external_signal_shadow/`

### Step 1: 跑 focused unit tests

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4b_lite_config.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_models.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_signals.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_replay.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_baseline.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4b_lite_funding_oi_price_crowding_replay.py -q
```

### Step 2: 跑相关回归测试

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_3_*.py \
  tests/research/external_signal_shadow/test_stage1_4a_*.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_*.py -q
```

### Step 3: 跑 ruff

```bash
PYTHONPATH=src:. uv run ruff check \
  src/research/external_signal_shadow/stage1_4b_lite_models.py \
  src/research/external_signal_shadow/stage1_4b_lite_signals.py \
  src/research/external_signal_shadow/stage1_4b_lite_replay.py \
  src/research/external_signal_shadow/stage1_4b_lite_baseline.py \
  src/research/external_signal_shadow/stage1_4b_lite_summary.py \
  scripts/external_signal_shadow/run_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  scripts/external_signal_shadow/review_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  tests/research/external_signal_shadow/test_stage1_4b_lite_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_4b_lite*.py
```

### Step 4: 生成 fixture summary / review smoke artifact

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  --funding-input tests/fixtures/external_signal_shadow/stage1_4b_lite_funding_rows.json \
  --oi-input tests/fixtures/external_signal_shadow/stage1_4b_lite_oi_rows.json \
  --price-input tests/fixtures/external_signal_shadow/stage1_4b_lite_price_rows.json \
  --fixture-run \
  --output-summary reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_summary.json

PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  --summary reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_summary.json \
  --output-review docs/reviews/2026-06-17-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-review_CN.md
```

### Step 5: 最小真实运行说明

如果要跑真实历史输入，使用现有 runtime normalized 路径或等价真实输入：

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4b_lite_funding_oi_price_crowding_replay.py \
  --funding-input data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_funding_normalized.jsonl \
  --oi-input data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl \
  --price-input data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_price_normalized.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_real_summary.json
```

注意：

- 这一步属于研究运行，不是本计划的最小交付要求。
- fixture smoke artifact 只能证明管线可运行，不能证明 crowding replay 研究结论成立。
- 如果真实输入字段名不统一，应优先在 runner 中做兼容或先生成 normalized runtime input，不要在 replay 核心逻辑里塞临时字段分支。

### Step 6: 最终工作区检查

```bash
git status --short
```

---

## 13. 本计划完成后的正确解释

实现完成后，只能证明：

```text
我们已经有一条参数冻结、as-of 对齐、baseline 硬约束的 crowding-only replay 管线。
```

不能证明：

```text
full composite 成功
liquidation 不重要
paper/live 可进入
funding/OI/price 已经找到可交易 alpha
```

如果最终结果为：

- `crowding_lite_failed`
  - 解释必须是：`crowding_only_failed_not_full_composite_failed`
- `crowding_lite_promising`
  - 下一步也只能是：
    - `prepare_stage1_4c_joint_decision_review`
    - 与 `LQ30` 联合解释
    - 继续积累 liquidation 或争取 vendor-grade sample
