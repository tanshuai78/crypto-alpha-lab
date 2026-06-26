# External Signal Shadow Lab Stage 1.5E Execution Feasibility Data Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 审计 Stage 1.5C `futures_contract_launch | futures_launch_long_attention_diagnostic | 12h` promising cell 是否具备最小执行可行性证据，明确 close-price replay 的收益是否可能被真实盘口摩擦吞掉。

**Architecture:** 新增独立 `stage1_5e_execution_feasibility_*` 模块和 runner。模块读取 Stage 1.5C / Stage 1.5C.1 / Stage 1.5D 证据，针对 1.5C promising cell 的 futures launch events 生成 execution feasibility audit：历史层只允许使用可复现的 kline / quote volume / mark-index proxy；实时层只允许为 Stage 1.5D 捕捉到的新事件采集 public readonly orderbook/depth snapshot。Stage 1.5E 不做 replay、不下单、不生成 strategy signal。

**Tech Stack:** Python 3.11、标准库 `urllib.request` / `urllib.parse`、JSON/JSONL、`configs/base.py`、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行边界

```text
decision = approved_with_major_required_fixes_absorbed
scope = execution_feasibility_data_audit_only
source_stage_required = stage1_5c_replay_completed_with_promising_futures_launch_12h_cell
primary_event_type = futures_contract_launch
primary_signed_mode = futures_launch_long_attention_diagnostic
primary_entry_delay_hours = 12
forward_return_allowed = false
replay_allowed = false
random_baseline_allowed = false
strategy_signal_allowed = false
SignalCandidate_allowed = false
TradeIntent_allowed = false
execution_engine_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
```

修订版已吸收的必须修正项：

```text
1. Historical kline proxy 不再使用 spread_proxy 语义。
2. entry_1h_range_bps / entry_4h_range_bps 明确乘以 10_000。
3. G1 / G2 按 cell-level 独立 summary，不允许混合 pass claim。
4. top-level event_count 使用 unique(symbol_event_id)，不重复计算 G1/G2。
5. Stage 1.5D pending 不阻塞 historical proxy audit。
6. live depth 只能用于 Stage 1.5D 新捕捉 live events，不能证明历史 candidates。
7. depth timestamp quality / snapshot age 规则已固定。
8. historical mark/index proxy 使用 kline endpoints；current premiumIndex 不得用于历史 divergence。
9. volume_collapse_ratio denominator 固定为 pre-entry 24h。
10. quote_volume pass rate 与 p95 range blocker 阈值进入 configs/base.py。
11. safety grep 改为精确禁止 import / constructor / endpoint / secret / sizing，而不误伤 *_allowed=false 字段。
```

Stage 1.5E 只能回答：

```text
1. Stage 1.5C 的 promising cell 是否缺少历史 orderbook / depth 证据？
2. 可用的历史 kline / quote volume / mark-index proxy 是否显示执行风险过高？
3. Stage 1.5D 后续 live event 是否需要实时采集 orderbook / depth 才能继续？
4. 是否允许进入 Stage 1.5F live execution-feasibility observer design？
```

Stage 1.5E 不能回答：

```text
是否有 alpha
是否可以 paper/live
是否可以 shadow execution
是否可以下单
是否可以用 close price 当真实成交价
```

### 0.1 核心现实约束

Binance public REST 可以获取当前 orderbook/depth，但不能免费、完整、可复现地获取 1.5C 历史 futures launch 当时的 orderbook/depth。

因此 Stage 1.5E 必须区分：

```text
historical_execution_proxy_audit:
  使用 15m futures klines、quote_volume、bar range、premium / mark-index proxy 做历史执行风险代理。
  只能输出 execution_feasibility_proxy_pass / fail / inconclusive。

historical_orderbook_depth_audit:
  如果本地存在历史 orderbook/depth archive，则可审计。
  如果不存在，必须输出 historical_orderbook_depth_unavailable = true。

live_orderbook_depth_observer_readiness:
  为 Stage 1.5D 捕捉到的新 futures launch event 设计实时 public depth 采集。
  只能证明后续 live observation 数据路径，不证明历史 replay 真实可成交。
```

不要把 `quote_volume` 或 kline range proxy 写成真实 slippage 证明。它们只能是 `execution_proxy`。

---

## 1. 输入 / 输出

### 1.1 Required inputs

Stage 1.5C rerun summary:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

Stage 1.5C replay candidates / results:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl
data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl
```

Stage 1.5C.1 futures coverage-pass events:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl
```

Stage 1.5C.1 futures kline archive:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl
```

Optional Stage 1.5D live source smoke outputs:

```text
data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

Optional historical orderbook/depth archive, if it exists:

```text
data/external_signal_shadow/stage1_5e/orderbook_depth_archive/*.jsonl
```

If optional historical orderbook/depth archive is absent, Stage 1.5E must not fail automatically. It must mark:

```text
historical_orderbook_depth_available = false
execution_feasibility_proven = false
execution_feasibility_status = execution_feasibility_inconclusive_depth_missing
```

### 1.2 Outputs

Candidate audit rows:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_candidates.jsonl
```

Historical proxy audit rows:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/historical_execution_proxy_audit.jsonl
```

Optional live depth request manifest:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/request_manifest.jsonl
```

Optional live orderbook/depth snapshots, only when explicitly running public readonly live collector:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/live_depth_snapshots.jsonl
```

Machine-readable summary:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
```

Chinese review:

```text
docs/reviews/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-review_CN.md
```

---

## 2. Decision Taxonomy

Allowed top-level decisions:

```text
stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer
stage1_5e_execution_feasibility_proxy_failed
stage1_5e_execution_feasibility_inconclusive_depth_missing
stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d
stage1_5e_execution_feasibility_invalid
```

Rules:

```text
invalid:
  upstream Stage 1.5C / 1.5C.1 evidence missing or invalid
  no futures launch long_attention 12h promising cell
  forbidden private/execution fields detected
  data schema corrupted beyond quarantine budget

proxy_failed:
  historical proxy shows severe execution risk:
    median_entry_15m_range_bps > configured max
    or p95_entry_15m_range_bps > configured p95 max
    or median_entry_1h_range_bps > configured max
    or median_entry_4h_range_bps > configured max
    or p05_pre_entry_24h_quote_volume_usdt < configured min
    or quote_volume_pass_rate < configured min pass rate
    or mark_index_divergence proxy exceeds configured max when historical mark/index klines are available

inconclusive_pending_stage1_5d:
  historical proxy is valid and not failed
  but Stage 1.5D formal source smoke is still pending/running
  live depth observer readiness cannot be finalized yet

inconclusive_depth_missing:
  historical proxy not failed
  but historical_orderbook_depth_available = false
  and live_depth_observer_evidence_available = false

ready_for_live_depth_observer:
  historical proxy not failed
  historical depth is missing or insufficient
  Stage 1.5D source smoke is operational or event-detection path exists
  next allowed action is Stage 1.5F live execution-feasibility observer design
```

No decision may permit:

```text
paper_trading_allowed != false
live_trading_allowed != false
execution_engine_allowed != false
alpha_interpretation_allowed != false
```

---

## 3. Pre-Registered Metrics

### 3.1 Historical kline execution proxy metrics

For each 1.5C promising candidate event, compute around the 12h entry bar:

```text
entry_bar_range_bps = (high - low) / open * 10_000
entry_bar_close_to_open_bps = (close - open) / open * 10_000
entry_1h_range_bps = (max(high over next 4 bars) / min(low over next 4 bars) - 1) * 10_000
entry_4h_range_bps = (max(high over next 16 bars) / min(low over next 16 bars) - 1) * 10_000
pre_entry_24h_quote_volume_usdt = sum(quote_volume over previous 96 bars)
post_entry_1h_quote_volume_usdt = sum(quote_volume over next 4 bars)
post_entry_4h_quote_volume_usdt = sum(quote_volume over next 16 bars)
median_same_symbol_pre_entry_24h_hourly_volume =
  median of 1h quote_volume buckets over [entry_time_ms - 24h, entry_time_ms)
volume_collapse_ratio_1h = post_entry_1h_quote_volume_usdt / median_same_symbol_pre_entry_24h_hourly_volume
```

These are proxy metrics. They do not prove fillability.

Do not emit or describe any kline-only historical field as `spread_proxy`, `historical_spread_proxy`, or `median_15m_spread_proxy_bps`. Kline OHLCV has no bid/ask spread.

### 3.2 Mark / index / premium proxy metrics

If public historical premium/index klines are available:

```text
mark_index_divergence_bps_at_entry
max_mark_index_divergence_bps_1h
max_mark_index_divergence_bps_4h
```

Historical mark/index audit must use historical kline endpoints:

```text
/fapi/v1/markPriceKlines
/fapi/v1/indexPriceKlines
/fapi/v1/premiumIndexKlines
```

Do not use current-state `/fapi/v1/premiumIndex` to populate historical entry-time divergence.

If unavailable:

```text
mark_index_proxy_available = false
mark_index_divergence_status = not_audited
```

Do not block the entire audit solely because mark/index proxy is unavailable. Record it as missing evidence.

### 3.3 Real-time orderbook/depth metrics

Only for Stage 1.5D live events or explicit fixture/live-public-readonly runs:

```text
best_bid
best_ask
mid_price
spread_bps = (best_ask - best_bid) / mid_price * 10_000
top_0_5pct_bid_depth_usdt
top_0_5pct_ask_depth_usdt
top_1pct_bid_depth_usdt
top_1pct_ask_depth_usdt
slippage_estimate_bps_for_500usdt_buy
slippage_estimate_bps_for_500usdt_sell
depth_snapshot_age_ms
depth_fetched_at_ms
exchange_event_time_ms
exchange_transaction_time_ms
depth_timestamp_quality = exchange_time | local_fetch_time_only
```

Depth status must be side-aware:

```text
long_attention diagnostic uses buy-side execution proxy:
  spread_bps
  top_0_5pct_ask_depth_usdt
  top_1pct_ask_depth_usdt
  slippage_estimate_bps_for_500usdt_buy
```

If Binance depth response does not provide exchange event / transaction timestamps, use local `depth_fetched_at_ms` for evidence timing and set:

```text
depth_snapshot_age_ms = null
depth_timestamp_quality = local_fetch_time_only
```

Do not fabricate snapshot age from local time only.

Live depth collection hard rule:

```text
If --live-public-readonly depth collection is enabled:
  require --stage1-5d-events-jsonl
  fetch depth only for Stage 1.5D newly detected live event rows
  require event age <= configured live depth observation window
  never fetch current depth for historical Stage 1.5C candidates
```

### 3.4 Summary aggregation metrics

Compute at cell level, not mixed top-level:

```text
cell_key = futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_or_G2
cell_event_count = unique(symbol_event_id, signed_mode, entry_delay_hours, filter_group)
candidate_event_days
symbols_with_events
historical_proxy_pass_count
historical_proxy_fail_count
historical_orderbook_depth_available_count
live_depth_snapshot_count
median_entry_bar_range_bps
p95_entry_bar_range_bps
median_entry_1h_range_bps
p95_entry_1h_range_bps
median_entry_4h_range_bps
p95_entry_4h_range_bps
median_pre_entry_24h_quote_volume_usdt
p05_pre_entry_24h_quote_volume_usdt
quote_volume_pass_rate
median_spread_bps_if_live_depth_available
p95_spread_bps_if_live_depth_available
median_slippage_bps_for_500usdt_buy_if_live_depth_available
p95_slippage_bps_for_500usdt_buy_if_live_depth_available
```

Top-level summary must not mix G1 and G2 into a single pass claim:

```json
{
  "cell_summaries": {
    "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay": {},
    "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only": {}
  },
  "ready_cells": [],
  "proxy_failed_cells": [],
  "inconclusive_cells": [],
  "top_level_unique_symbol_event_count": 0
}
```

Top-level event count must use `unique(symbol_event_id)` and must not double-count the same event across G1/G2.

Do not aggregate long/short modes. Stage 1.5E v1 audits only long_attention promising cell.

---

## 4. Thresholds To Add In `configs/base.py`

All thresholds must be added to `configs/base.py`; no magic numbers in `src/`.

```python
# ─── External Signal Shadow Lab Stage 1.5E: Execution Feasibility Data Audit ───

EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_EVENT_TYPE = "futures_contract_launch"
EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_SIGNED_MODE = "futures_launch_long_attention_diagnostic"
EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_ENTRY_DELAY_HOURS = 12
EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_FILTER_GROUPS = (
    "G1_source_event_after_first_hour_delay",
    "G2_price_coverage_only",
)

EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_COUNT = 30
EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_SYMBOLS = 3

EXTERNAL_SIGNAL_STAGE1_5E_MIN_PRE_ENTRY_24H_QUOTE_VOLUME_USDT = 50_000_000
EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_15M_RANGE_BPS = 300.0
EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_1H_RANGE_BPS = 600.0
EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_4H_RANGE_BPS = 1_200.0
EXTERNAL_SIGNAL_STAGE1_5E_MIN_QUOTE_VOLUME_PASS_RATE = 0.70
EXTERNAL_SIGNAL_STAGE1_5E_P95_RANGE_MULTIPLIER_BLOCK = 2.0
EXTERNAL_SIGNAL_STAGE1_5E_MAX_MARK_INDEX_DIVERGENCE_BPS = 50.0

EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_NOTIONAL_USDT = 500.0
EXTERNAL_SIGNAL_STAGE1_5E_MAX_LIVE_SPREAD_BPS = 20.0
EXTERNAL_SIGNAL_STAGE1_5E_MIN_TOP_0_5PCT_ASK_DEPTH_USDT = 10_000.0
EXTERNAL_SIGNAL_STAGE1_5E_MIN_TOP_1PCT_ASK_DEPTH_USDT = 25_000.0
EXTERNAL_SIGNAL_STAGE1_5E_MAX_SLIPPAGE_BPS_FOR_500USDT = 50.0

EXTERNAL_SIGNAL_STAGE1_5E_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
EXTERNAL_SIGNAL_STAGE1_5E_DEPTH_PATH = "/fapi/v1/depth"
EXTERNAL_SIGNAL_STAGE1_5E_BOOK_TICKER_PATH = "/fapi/v1/ticker/bookTicker"
EXTERNAL_SIGNAL_STAGE1_5E_TICKER_24H_PATH = "/fapi/v1/ticker/24hr"
EXTERNAL_SIGNAL_STAGE1_5E_MARK_PRICE_KLINES_PATH = "/fapi/v1/markPriceKlines"
EXTERNAL_SIGNAL_STAGE1_5E_INDEX_PRICE_KLINES_PATH = "/fapi/v1/indexPriceKlines"
EXTERNAL_SIGNAL_STAGE1_5E_PREMIUM_INDEX_KLINES_PATH = "/fapi/v1/premiumIndexKlines"
EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_OBSERVATION_MAX_EVENT_AGE_MS = 24 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5E_REQUEST_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5E_RETRY_BUDGET = 2
EXTERNAL_SIGNAL_STAGE1_5E_REQUEST_SLEEP_SEC = 0.2
EXTERNAL_SIGNAL_STAGE1_5E_MAX_PUBLIC_REQUESTS_PER_RUN = 500
```

Threshold rationale:

```text
20 bps max spread and 50 bps max 500 USDT slippage are intentionally loose.
If a futures launch cannot pass even these loose filters, close-price replay is not execution-relevant.
50M USDT pre-entry 24h quote volume matches Stage 1.5C liquidity proxy threshold.
Entry range thresholds are diagnostic blockers for thin-book / repricing / wick risk, not trading stop rules.
```

---

## 5. Implementation Tasks

### Task 1: Add Stage 1.5E Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_config.py`

**Step 1: Write failing config tests**

```python
from configs import base


def test_stage1_5e_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_EVENT_TYPE == "futures_contract_launch"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_SIGNED_MODE == "futures_launch_long_attention_diagnostic"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_ENTRY_DELAY_HOURS == 12
    assert "G1_source_event_after_first_hour_delay" in base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_FILTER_GROUPS
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_COUNT >= 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MAX_LIVE_SPREAD_BPS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MAX_SLIPPAGE_BPS_FOR_500USDT > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MIN_QUOTE_VOLUME_PASS_RATE == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_P95_RANGE_MULTIPLIER_BLOCK == 2.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_DEPTH_PATH == "/fapi/v1/depth"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MARK_PRICE_KLINES_PATH == "/fapi/v1/markPriceKlines"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PREMIUM_INDEX_KLINES_PATH == "/fapi/v1/premiumIndexKlines"
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_config.py -q
```

Expected: FAIL because constants do not exist.

**Step 3: Add constants**

Add the constants from Section 4 to `configs/base.py`.

**Step 4: Run test to verify it passes**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_config.py -q
```

Expected: PASS.

---

### Task 2: Add Models And Decision Enums

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_models.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_models import (
    ExecutionFeasibilityDecision,
    ExecutionFeasibilityCandidate,
)


def test_decision_enum_values_are_fixed():
    assert ExecutionFeasibilityDecision.READY_FOR_LIVE_DEPTH_OBSERVER.value == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    assert ExecutionFeasibilityDecision.PROXY_FAILED.value == "stage1_5e_execution_feasibility_proxy_failed"
    assert ExecutionFeasibilityDecision.INCONCLUSIVE_DEPTH_MISSING.value == "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    assert ExecutionFeasibilityDecision.INCONCLUSIVE_PENDING_STAGE1_5D.value == "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"
    assert ExecutionFeasibilityDecision.INVALID.value == "stage1_5e_execution_feasibility_invalid"


def test_candidate_defaults_do_not_allow_execution():
    row = ExecutionFeasibilityCandidate(
        symbol="ABCUSDT",
        symbol_event_id="evt-1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        entry_delay_hours=12,
        filter_group="G1_source_event_after_first_hour_delay",
        entry_time_ms=1_700_000_000_000,
    ).to_dict()

    assert row["execution_engine_allowed"] is False
    assert row["paper_trading_allowed"] is False
    assert row["live_trading_allowed"] is False
    assert row["alpha_interpretation_allowed"] is False
    assert row["execution_feasibility_proven"] is False
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_models.py -q
```

Expected: FAIL because module does not exist.

**Step 3: Implement models**

Implement:

```python
from dataclasses import dataclass, asdict
from enum import Enum


class ExecutionFeasibilityDecision(str, Enum):
    READY_FOR_LIVE_DEPTH_OBSERVER = "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    PROXY_FAILED = "stage1_5e_execution_feasibility_proxy_failed"
    INCONCLUSIVE_DEPTH_MISSING = "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    INCONCLUSIVE_PENDING_STAGE1_5D = "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"
    INVALID = "stage1_5e_execution_feasibility_invalid"


@dataclass(frozen=True)
class ExecutionFeasibilityCandidate:
    symbol: str
    symbol_event_id: str
    event_type: str
    signed_mode: str
    entry_delay_hours: int
    filter_group: str
    entry_time_ms: int
    execution_engine_allowed: bool = False
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    alpha_interpretation_allowed: bool = False
    execution_feasibility_proven: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
```

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_models.py -q
```

Expected: PASS.

---

### Task 3: Validate Upstream Evidence And Load Promising Candidates

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_loader.py`

**Step 1: Write failing tests**

```python
import json

import pytest

from src.research.external_signal_shadow.stage1_5e_execution_feasibility_loader import (
    load_promising_12h_long_attention_candidates,
    validate_stage1_5e_upstream_evidence,
)


def test_validate_upstream_requires_stage1_5c_promising_12h_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is True
    assert result["primary_promising_cell_present"] is True


def test_validate_upstream_rejects_missing_promising_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [],
    }))
    c1_summary.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_accepts_g2_only_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is True
    assert result["primary_promising_cell_present"] is True


def test_load_promising_candidates_filters_only_12h_long_attention_primary_rows(tmp_path):
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        "\n".join([
            json.dumps({
                "symbol": "ABCUSDT",
                "symbol_event_id": "evt-1",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_long_attention_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G1_source_event_after_first_hour_delay",
                "entry_time_ms": 1_000,
            }),
            json.dumps({
                "symbol": "ABCUSDT",
                "symbol_event_id": "evt-1",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_short_access_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G1_source_event_after_first_hour_delay",
                "entry_time_ms": 1_000,
            }),
            json.dumps({
                "symbol": "XYZUSDT",
                "symbol_event_id": "evt-2",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_long_attention_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G2_price_coverage_only",
                "entry_time_ms": 2_000,
            }),
        ])
    )

    loaded = load_promising_12h_long_attention_candidates(candidates)
    assert len(loaded) == 2
    assert {row["filter_group"] for row in loaded} == {
        "G1_source_event_after_first_hour_delay",
        "G2_price_coverage_only",
    }
```

**Step 2: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_loader.py -q
```

Expected: FAIL because module does not exist.

**Step 3: Implement loader**

Implementation requirements:

```text
validate_stage1_5e_upstream_evidence:
  accepts G1 or G2 or any configured primary filter group, including G2-only upstream evidence
  rejects 1h / 4h cells
  rejects short_access cells
  rejects missing research_result_valid
  rejects any paper/live/execution/alpha true flag

load_promising_12h_long_attention_candidates:
  reads JSONL
  skips invalid JSON with quarantine count
  keeps only futures_contract_launch + long_attention + 12h + configured filter groups
  keeps both G1 and G2 rows when both are present
  dedupes by symbol_event_id + signed_mode + entry_delay_hours + filter_group
```

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_loader.py -q
```

Expected: PASS.

---

### Task 4: Compute Historical Kline Execution Proxy Metrics

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_proxy.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_proxy.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_proxy import (
    compute_entry_proxy_metrics,
)


def test_compute_entry_proxy_metrics_uses_entry_and_forward_bars():
    bars = []
    start = 1_000
    interval = 15 * 60 * 1000
    for i in range(20):
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": start + i * interval,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "quote_volume": 1_000_000.0,
        })

    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=start + 2 * interval,
        bars=bars,
    )

    assert metrics["entry_bar_found"] is True
    assert metrics["entry_bar_range_bps"] == 200.0
    assert 200.0 < metrics["entry_1h_range_bps"] < 205.0
    assert 200.0 < metrics["entry_4h_range_bps"] < 205.0
    assert metrics["post_entry_1h_quote_volume_usdt"] == 4_000_000.0
    assert metrics["volume_collapse_ratio_1h"] == 1.0
    assert "spread_proxy_bps" not in metrics
    assert "historical_spread_proxy" not in metrics


def test_compute_entry_proxy_metrics_missing_entry_bar_is_not_pass():
    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=999_999,
        bars=[],
    )

    assert metrics["entry_bar_found"] is False
    assert metrics["historical_proxy_status"] == "missing_entry_bar"


def test_volume_collapse_ratio_denominator_uses_pre_entry_24h_only():
    interval = 15 * 60 * 1000
    entry_time_ms = 100 * interval
    bars = []
    for i in range(120):
        quote_volume = 1_000_000.0 if i < 100 else 100_000_000.0
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": i * interval,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "quote_volume": quote_volume,
        })

    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=entry_time_ms,
        bars=bars,
    )

    assert metrics["median_same_symbol_pre_entry_24h_hourly_volume"] == 4_000_000.0
    assert metrics["volume_collapse_ratio_1h"] == 100.0
```

**Step 2: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_proxy.py -q
```

Expected: FAIL because module does not exist.

**Step 3: Implement proxy**

Implementation requirements:

```text
compute_entry_proxy_metrics:
  index bars by symbol
  entry_bar = first bar_start_ms >= entry_time_ms
  never use bars before entry_time_ms as entry bar
  compute 15m / 1h / 4h range proxies in bps using * 10_000
  compute quote volume proxies
  compute median_same_symbol_pre_entry_24h_hourly_volume only from [entry_time_ms - 24h, entry_time_ms)
  return missing statuses instead of raising on incomplete windows
  never emit spread_proxy fields from kline-only data
```

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_proxy.py -q
```

Expected: PASS.

---

### Task 5: Add Public Readonly Depth Client And Slippage Estimator

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_client.py`
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_depth.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_depth.py`

**Step 1: Write failing depth tests**

```python
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_depth import (
    compute_depth_metrics,
    normalize_depth_timestamp_fields,
)


def test_compute_depth_metrics_for_buy_side_500usdt():
    orderbook = {
        "bids": [["99.9", "100"], ["99.0", "100"]],
        "asks": [["100.1", "2"], ["100.2", "3"], ["101.0", "100"]],
    }

    metrics = compute_depth_metrics(orderbook, notional_usdt=500.0)

    assert metrics["spread_bps"] > 0
    assert metrics["top_0_5pct_ask_depth_usdt"] > 0
    assert metrics["top_1pct_ask_depth_usdt"] > metrics["top_0_5pct_ask_depth_usdt"]
    assert metrics["slippage_estimate_bps_for_500usdt_buy"] >= 0


def test_compute_depth_metrics_marks_insufficient_depth():
    orderbook = {
        "bids": [["99.9", "1"]],
        "asks": [["100.1", "0.1"]],
    }

    metrics = compute_depth_metrics(orderbook, notional_usdt=500.0)

    assert metrics["buy_depth_sufficient_for_500usdt"] is False
    assert metrics["depth_status"] == "insufficient_ask_depth"


def test_depth_timestamp_quality_local_fetch_time_only_when_exchange_time_missing():
    fields = normalize_depth_timestamp_fields({"lastUpdateId": 123}, fetched_at_ms=1_700_000_000_000)

    assert fields["depth_fetched_at_ms"] == 1_700_000_000_000
    assert fields["exchange_event_time_ms"] is None
    assert fields["exchange_transaction_time_ms"] is None
    assert fields["depth_snapshot_age_ms"] is None
    assert fields["depth_timestamp_quality"] == "local_fetch_time_only"
```

**Step 2: Write failing client tests**

```python
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_client import (
    build_depth_url,
    fetch_public_json,
    is_allowed_public_url,
)


def test_depth_url_uses_binance_fapi_public_endpoint():
    url = build_depth_url("ABCUSDT", limit=100)
    assert url.startswith("https://fapi.binance.com/fapi/v1/depth")
    assert "symbol=ABCUSDT" in url
    assert "limit=100" in url


def test_public_url_rejects_private_or_non_binance_hosts():
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/depth?symbol=ABCUSDT")
    assert not is_allowed_public_url("https://evil-binance.com/fapi/v1/depth")
    assert not is_allowed_public_url("https://fapi.binance.com.evil.io/fapi/v1/depth")


def test_client_rejects_redirect_to_non_binance_host(monkeypatch):
    class FakeResponse:
        url = "https://evil.example.com/fapi/v1/depth"
        status = 200

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(_request, timeout):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = fetch_public_json("https://fapi.binance.com/fapi/v1/depth?symbol=ABCUSDT", live_public_readonly=True)
    assert result["ok"] is False
    assert result["error"] == "redirect_final_host_not_allowed"
```

**Step 3: Run tests**

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_client.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_depth.py \
  -q
```

Expected: FAIL because modules do not exist.

**Step 4: Implement client and depth metrics**

Implementation requirements:

```text
client:
  public endpoints only
  host must be fapi.binance.com
  final redirect host must be revalidated if fetch_public_json follows redirects
  no API keys
  write request manifest row for every live request
  support fixture mode without network

depth:
  parse bids/asks as Decimal or float with explicit validation
  compute mid from best bid/ask
  compute top 0.5% and 1% depth separately for bid and ask
  estimate buy-side slippage for 500 USDT by walking asks
  estimate sell-side slippage by walking bids
  never infer depth from kline quote volume
  depth_snapshot_age_ms is null when exchange event/transaction time is missing
```

**Step 5: Run tests**

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_client.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_depth.py \
  -q
```

Expected: PASS.

---

### Task 6: Build Audit Summary Decision Engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5e_execution_feasibility_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_summary.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_summary import (
    build_execution_feasibility_summary,
)


def test_summary_inconclusive_when_proxy_passes_but_depth_missing():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        proxy_rows=[{"historical_proxy_pass": True, "symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="operational_unvalidated",
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    assert summary["execution_feasibility_proven"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert cell in summary["cell_summaries"]
    assert cell in summary["inconclusive_cells"]


def test_summary_proxy_failed_when_entry_range_too_wide():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        proxy_rows=[{"historical_proxy_pass": False, "proxy_fail_reasons": ["entry_15m_range_too_wide"], "entry_bar_range_bps": 900.0, "cell_key": cell, "symbol_event_id": f"evt-{i}"} for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed"
    assert "entry_15m_range_too_wide" in summary["blockers"]
    assert cell in summary["proxy_failed_cells"]


def test_summary_proxy_failed_when_quote_volume_pass_rate_below_threshold():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    candidate_rows = [{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)]
    proxy_rows = []
    for i in range(30):
        proxy_rows.append({
            "historical_proxy_pass": i < 20,
            "proxy_fail_reasons": [] if i < 20 else ["pre_entry_24h_quote_volume_below_min"],
            "quote_volume_pass": i < 20,
            "symbol_event_id": f"evt-{i}",
            "cell_key": cell,
        })

    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=candidate_rows,
        proxy_rows=proxy_rows,
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["cell_summaries"][cell]["quote_volume_pass_rate"] < 0.70
    assert summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed"
    assert "quote_volume_pass_rate_below_threshold" in summary["blockers"]


def test_summary_ready_for_live_depth_observer_when_proxy_ok_and_source_ready():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        proxy_rows=[{"historical_proxy_pass": True, "symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="operational_unvalidated",
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    assert summary["allowed_next_action"] == "write_stage1_5f_live_execution_feasibility_observer_design"
    assert cell in summary["ready_cells"]


def test_stage1_5d_pending_does_not_block_historical_proxy_audit():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        proxy_rows=[{"historical_proxy_pass": True, "symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell} for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="pending",
    )

    assert summary["historical_proxy_audit_valid"] is True
    assert summary["source_smoke_dependency_status"] == "pending"
    assert summary["decision"] == "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"


def test_top_level_event_count_does_not_double_count_g1_g2_same_symbol_event():
    g1 = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    g2 = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"
    candidates = []
    proxies = []
    for i in range(30):
        for cell in (g1, g2):
            row = {"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "cell_key": cell}
            candidates.append(row)
            proxies.append({**row, "historical_proxy_pass": True})

    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=candidates,
        proxy_rows=proxies,
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="pending",
    )

    assert summary["top_level_unique_symbol_event_count"] == 30
    assert summary["cell_summaries"][g1]["cell_event_count"] == 30
    assert summary["cell_summaries"][g2]["cell_event_count"] == 30


def test_summary_invalid_when_candidate_count_below_minimum():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": "2026-06-01", "cell_key": cell} for i in range(10)],
        proxy_rows=[{"historical_proxy_pass": True, "symbol_event_id": f"evt-{i}", "cell_key": cell} for i in range(10)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_invalid"
    assert "insufficient_candidate_event_count" in summary["blockers"]
```

**Step 2: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_summary.py -q
```

Expected: FAIL because module does not exist.

**Step 3: Implement summary**

Summary must output:

```json
{
  "decision": "...",
  "research_result_valid": false,
  "execution_feasibility_proven": false,
  "historical_orderbook_depth_available": false,
  "historical_proxy_audit_valid": true,
  "live_depth_snapshot_available": false,
  "top_level_unique_symbol_event_count": 0,
  "cell_summaries": {},
  "ready_cells": [],
  "proxy_failed_cells": [],
  "inconclusive_cells": [],
  "candidate_event_days": 0,
  "symbols_with_events": 0,
  "median_entry_bar_range_bps": null,
  "p95_entry_bar_range_bps": null,
  "median_entry_1h_range_bps": null,
  "p95_entry_1h_range_bps": null,
  "median_entry_4h_range_bps": null,
  "p95_entry_4h_range_bps": null,
  "median_pre_entry_24h_quote_volume_usdt": null,
  "median_live_spread_bps": null,
  "median_live_slippage_bps_for_500usdt_buy": null,
  "blockers": [],
  "allowed_next_action": "...",
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false
}
```

`research_result_valid` should mean “this audit result is valid as an execution-feasibility data audit,” not alpha validity. It must remain `false` if fixture/debug-only.

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_summary.py -q
```

Expected: PASS.

---

### Task 7: Add Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5e_execution_feasibility_audit.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5e_execution_feasibility_audit.py`

**Step 1: Write failing tests**

```python
import json
import sys

from scripts.external_signal_shadow.run_stage1_5e_execution_feasibility_audit import main


def test_runner_requires_upstream_evidence(tmp_path, monkeypatch):
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(tmp_path / "missing_5c.json"),
        "--stage1-5c1-summary", str(tmp_path / "missing_5c1.json"),
        "--output-summary", str(summary),
    ])

    rc = main()
    assert rc == 2
    data = json.loads(summary.read_text())
    assert data["decision"] == "stage1_5e_execution_feasibility_invalid"
    assert "upstream_evidence_missing_or_invalid" in data["blockers"]


def test_runner_fixture_proxy_only_writes_inconclusive_summary(tmp_path, monkeypatch):
    c_summary = tmp_path / "stage1_5c.json"
    c1_summary = tmp_path / "stage1_5c1.json"
    candidates = tmp_path / "candidates.jsonl"
    klines = tmp_path / "klines.jsonl"
    output_summary = tmp_path / "summary.json"

    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    candidates.write_text("")
    klines.write_text("")

    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(c_summary),
        "--stage1-5c1-summary", str(c1_summary),
        "--candidates-jsonl", str(candidates),
        "--klines-jsonl", str(klines),
        "--output-summary", str(output_summary),
        "--fixture-proxy-only",
    ])

    rc = main()
    assert rc in (0, 1)
    data = json.loads(output_summary.read_text())
    assert data["paper_trading_allowed"] is False
    assert data["live_trading_allowed"] is False


def test_runner_live_depth_requires_stage1_5d_event_rows(tmp_path, monkeypatch):
    c_summary = tmp_path / "stage1_5c.json"
    c1_summary = tmp_path / "stage1_5c1.json"
    candidates = tmp_path / "candidates.jsonl"
    klines = tmp_path / "klines.jsonl"
    output_summary = tmp_path / "summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    candidates.write_text("")
    klines.write_text("")

    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(c_summary),
        "--stage1-5c1-summary", str(c1_summary),
        "--candidates-jsonl", str(candidates),
        "--klines-jsonl", str(klines),
        "--output-summary", str(output_summary),
        "--live-public-readonly",
    ])

    rc = main()
    assert rc == 2
    data = json.loads(output_summary.read_text())
    assert "stage1_5d_events_required_for_live_depth" in data["blockers"]
    assert data["live_depth_snapshot_available"] is False
```

**Step 2: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5e_execution_feasibility_audit.py -q
```

Expected: FAIL because script does not exist.

**Step 3: Implement runner**

CLI:

```text
--stage1-5c-summary
--stage1-5c1-summary
--candidates-jsonl
--klines-jsonl
--stage1-5d-summary optional
--stage1-5d-events-jsonl optional, required when --live-public-readonly depth collection is enabled
--historical-depth-jsonl optional
--live-public-readonly optional, required for depth endpoint network calls
--output-root
--output-summary
--fixture-proxy-only
```

Rules:

```text
Without --live-public-readonly:
  do not call public depth endpoint
  historical proxy audit is allowed from local files

With --live-public-readonly:
  require --stage1-5d-events-jsonl
  only call fapi.binance.com public endpoints for symbols from Stage 1.5D live event rows
  require Stage 1.5D event age <= EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_OBSERVATION_MAX_EVENT_AGE_MS
  never fetch current depth for historical Stage 1.5C candidates
  enforce request budget
  write request_manifest
```

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5e_execution_feasibility_audit.py -q
```

Expected: PASS.

---

### Task 8: Add Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5e_execution_feasibility_audit.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5e_execution_feasibility_audit.py`

**Step 1: Write failing tests**

```python
import json
import sys

from scripts.external_signal_shadow.review_stage1_5e_execution_feasibility_audit import main


def test_review_renders_decision_and_safety_boundaries(tmp_path, monkeypatch):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_inconclusive_depth_missing",
        "execution_feasibility_proven": False,
        "historical_orderbook_depth_available": False,
        "top_level_unique_symbol_event_count": 62,
        "cell_summaries": {
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay": {
                "cell_event_count": 62,
                "median_entry_bar_range_bps": 180.0,
                "p95_entry_bar_range_bps": 520.0,
            }
        },
        "median_entry_bar_range_bps": 180.0,
        "p95_entry_bar_range_bps": 520.0,
        "blockers": ["historical_orderbook_depth_missing"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5e_execution_feasibility_audit.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ])

    assert main() == 0
    text = review.read_text()
    assert "stage1_5e_execution_feasibility_inconclusive_depth_missing" in text
    assert "historical_orderbook_depth_available" in text
    assert "paper_trading_allowed" in text
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in text
```

**Step 2: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5e_execution_feasibility_audit.py -q
```

Expected: FAIL because script does not exist.

**Step 3: Implement review generator**

Review sections:

```text
1. Decision
2. Upstream Evidence
3. Cell-Level Historical Proxy Audit
4. Historical Orderbook / Depth Evidence
5. Live Depth Snapshot Evidence
6. Why close-price replay is still not execution proof
7. Safety Boundaries
8. Allowed Next Action
```

**Step 4: Run test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5e_execution_feasibility_audit.py -q
```

Expected: PASS.

---

### Task 9: Add Smoke Commands And Verification Gates

**Files:**
- No new source file required unless previous tasks need small fixes.

**Step 1: Verify gitignore covers data outputs**

```bash
mkdir -p data/external_signal_shadow/stage1_5e/execution_feasibility
git check-ignore -v data/external_signal_shadow/stage1_5e/execution_feasibility/
```

Expected: output indicates `data/` or equivalent ignore rule.

If not ignored, stop and fix `.gitignore` before running smoke.

**Step 2: Run fixture/proxy-only smoke**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5e_execution_feasibility_audit.py \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --candidates-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl \
  --klines-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl \
  --output-root data/external_signal_shadow/stage1_5e/execution_feasibility \
  --output-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --fixture-proxy-only
```

Expected:

```text
No network calls.
No paper/live/execution/alpha flags true.
Decision is one of:
  stage1_5e_execution_feasibility_proxy_failed
  stage1_5e_execution_feasibility_inconclusive_depth_missing
  stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d
  stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer
```

**Step 3: Generate review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5e_execution_feasibility_audit.py \
  --summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-review docs/reviews/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-review_CN.md
```

Expected: review exists and contains no `TODO` / `TBD` / `placeholder` / `FIXME`.

**Step 4: Run targeted tests**

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_config.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_models.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_loader.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_proxy.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_client.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_depth.py \
  tests/research/external_signal_shadow/test_stage1_5e_execution_feasibility_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5e_execution_feasibility_audit.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5e_execution_feasibility_audit.py \
  -q
```

Expected: all pass.

**Step 5: Run regression tests for upstream stages**

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_*.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_*.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: all pass.

**Step 6: Safety grep**

```bash
rg -n "from .*TradeIntent|TradeIntent\\(|from .*SignalCandidate|SignalCandidate\\(|order_endpoint|account_endpoint|private_ws|apiKey|secret|position sizing" \
  src/research/external_signal_shadow/stage1_5e_*.py \
  scripts/external_signal_shadow/*stage1_5e*
```

Expected: no hits. Fields such as `TradeIntent_allowed = false` / `SignalCandidate_allowed = false` in docs or data schemas are allowed; imports, constructors, endpoints, secrets, and sizing logic are not.

**Step 7: Lint**

```bash
PYTHONPATH=src:. uv run ruff check \
  src/research/external_signal_shadow/stage1_5e_*.py \
  scripts/external_signal_shadow/*stage1_5e* \
  tests/research/external_signal_shadow/test_stage1_5e_*.py \
  tests/scripts/external_signal_shadow/*stage1_5e*
```

Expected: all checks passed.

---

## 6. Completion Criteria

Stage 1.5E implementation is complete only if:

```text
1. All Stage 1.5E constants are in configs/base.py.
2. Upstream evidence gate rejects invalid Stage 1.5C / 1.5C.1 summaries.
3. Loader keeps only futures_contract_launch long_attention 12h promising candidates.
4. Historical kline proxy metrics are computed without lookahead.
5. Historical orderbook/depth absence is reported as inconclusive_depth_missing, not hidden.
6. Public depth client is public-readonly, host-allowlisted, and request-manifested.
7. Summary never sets paper/live/execution/alpha flags true.
8. Review clearly states close-price replay is not execution proof.
9. Targeted tests and upstream regression tests pass.
10. Safety grep has zero forbidden-code hits while allowing explicit `*_allowed = false` safety fields.
```

Do not commit automatically. Show `git status --short` and wait for user confirmation.

---

## 7. Expected Outcomes

Likely outcomes:

```text
stage1_5e_execution_feasibility_inconclusive_depth_missing:
  Historical proxy does not kill the idea, but we lack historical orderbook/depth.
  Next action: Stage 1.5F live execution-feasibility observer design.

stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d:
  Historical proxy audit can run, but the formal 24h Stage 1.5D source smoke is still pending.
  Next action: wait for Stage 1.5D completion, then rerun/refresh Stage 1.5E summary.

stage1_5e_execution_feasibility_proxy_failed:
  Kline proxy already shows severe wick / volume / mark-index risk.
  Next action: stop execution-readiness path; keep futures launch as research-only phenomenon.

stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer:
  Historical proxy acceptable, but live depth observation is still required.
  Next action: write Stage 1.5F live execution-feasibility observer design.
```

Important:

```text
No Stage 1.5E outcome permits paper trading.
No Stage 1.5E outcome permits live trading.
No Stage 1.5E outcome permits execution engine integration.
```
