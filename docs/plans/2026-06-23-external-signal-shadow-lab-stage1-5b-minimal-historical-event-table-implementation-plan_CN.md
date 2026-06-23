# External Signal Shadow Lab Stage 1.5B Minimal Historical Event Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现 `Stage 1.5B Minimal Historical Event Table`，把 Stage 1.5A 审计通过的 Binance 高可信公告候选整理成可复现、可审计、可供 Stage 1.5C loader/review 再审核的 external catalyst event table。

**Architecture:** 新增独立 `stage1_5b_event_table_*` 模块，只消费 Stage 1.5A 通过的 source/event-type 组合；输入是人工复核后的 article-level JSONL 与 Stage 1.5A source audit summary，输出 raw article table、symbol-expanded normalized event table、normalization summary 与中文 review。1.5B 不做价格 join、不做 forward return、不做 baseline、不做交易解释，也不决定任何 row 是否为 Stage 1.5C replay candidate。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、JSON/JSONL、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行边界

```text
decision = approved_with_required_fixes
scope = minimal_historical_event_table_only
price_join_allowed = false
forward_return_allowed = false
replay_allowed = false
context_label_join_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

必须在 coding 前吸收以下修正：

1. `stage1_5c_candidate_allowed` 不得设为 true；1.5B 只能标记 `stage1_5c_review_pending = true`，是否成为 replay candidate 由 1.5C 决定。
2. `BASEUSDT` 只是研究符号归一化假设，必须标记 market pair / price history / tradability 未验证。
3. 所有方向字段必须为空：`directional_hypothesis = undefined`、`signed_direction = null`、`long_allowed = false`、`short_allowed = false`。
4. Delisting 必须保留 `notice_time_ms` 与 `effective_time_ms` 占位，1.5B 不解析实际下架时间。
5. Summary 必须强制输出 article-level 与 symbol-level event type counts。
6. Symbol rows 必须包含 Stage 1.5A summary/review provenance。
7. 1.5B 不得输出 funding/OI/liquidation/BTC regime/context label 字段。
8. Allowed event types 必须取 config、Stage 1.5A source recommendation、Stage 1.5A event_type decision 三者交集。
9. `100` 只作为首版目标规模，不作为失败硬上限。


### 0.1 当前已通过的上游证据

Stage 1.5A 已完成 Binance source audit：

```text
input_raw_candidate_rows = 236
reviewed_high_confidence_article_rows = 94
rejected_rows = 142
stage1_5a_overall_decision = source_audit_passed
research_result_valid = true
historical_events_found_after_symbol_expansion = 194
unique_event_days = 81
symbols_with_events = 191
source_integrity_pass_rate = 100%
trade_pair_mapping_pass_rate = 100%
timestamp_quality_high_or_medium_ratio = 100%
schema_quarantine_count = 0
```

允许进入 Stage 1.5B 的 source/event-type 组合只能是：

```text
source = binance_official_announcements_like_rows_source
allowed_event_types = [
  exchange_delisting_notice,
  futures_contract_launch
]
```

不得把以下 event types 带入 1.5B：

```text
margin_enablement
trading_pair_removal
trading_pair_addition_for_existing_liquid_asset
major_exchange_status_event
major_unlock_event
large_scheduled_token_emission
new_coin_listing
whale_deposit
```

### 0.2 30-100 条门槛解释

Stage 1.5B 的 `30-100 条高可信 external catalyst event JSONL` 指的是 **article-level source event rows**，不是 symbol-expanded rows。

当前输入：

```text
article_level_rows = 94  # pass, within 30-100
symbol_expanded_rows = 194  # report-only, allowed to exceed 100
```

原因：一条 Binance delisting 公告可能同时包含多个 symbol。后续 replay 需要 symbol-level event rows，但 source audit 和人工复核的密度门槛应按公告级 row 计算，否则会把多币公告错误地当成多个独立 source events。

### 0.3 Scope

本阶段只允许：

```text
read high-confidence Stage 1.5A candidate JSONL
verify Stage 1.5A summary passed
filter allowed source/event-type combinations
copy raw article table with hashes
expand article rows into symbol-level normalized rows
compute normalization/source coverage summary
generate Chinese review
```

本阶段禁止：

```text
price / OHLCV join
funding / OI / liquidation context join
forward return
MFE / MAE
random baseline
filter matrix replay groups
alpha interpretation
paper trading
live trading
execution intent
position sizing
```

Summary 顶层必须固定：

```json
{
  "stage": "external_signal_shadow_lab_stage1_5b",
  "scope": "minimal_historical_event_table_only",
  "source_audit_required": true,
  "source_audit_passed_required": true,
  "price_join_allowed": false,
  "forward_return_allowed": false,
  "replay_allowed": false,
  "alpha_interpretation_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "event_type_mixing_allowed_for_replay_pass": false
}
```

---

## 1. Expected Inputs / Outputs

### 1.1 Inputs

Primary input:

```text
data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_reviewed_high_confidence.jsonl
```

Required upstream audit summary:

```text
data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json
```

Required upstream review evidence:

```text
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md
```

Input row shape currently observed:

```json
{
  "event_type_candidate": "futures_contract_launch",
  "manual_review_required": true,
  "manual_review_status": "reviewed_high_confidence",
  "source_capture_method": "semi_auto_collector",
  "source_line": 3,
  "source_name": "binance_official_announcements",
  "source_url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
  "symbol": ["ARX"],
  "time": 1782185438167,
  "title": "Binance Futures Will Launch USDⓈ-Margined ARXUSDT Perpetual Contract (2026-06-23)",
  "url": "https://www.binance.com/en/support/announcement/7fa4e8b3ced94b4c8c189a4593dbce9b"
}
```

### 1.2 Outputs

```text
data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl
```

Article-level rows, one row per manually reviewed source announcement.

```text
data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl
```

Symbol-level rows, one row per `(article_event, symbol)` pair.

```text
data/external_signal_shadow/stage1_5b/normalization_summary.json
```

Machine-readable summary.

```text
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md
```

Chinese review.

---

## 2. Normalized Schema

### 2.1 Raw article row schema

Each row in `external_catalyst_events_raw.jsonl` must include:

```json
{
  "article_event_id": "sha256(title|time|url)",
  "stage1_5a_source_line": 3,
  "source_name": "binance_official_announcements",
  "source_profile": "binance_official_announcements_like_rows",
  "source_capture_method": "semi_auto_collector",
  "source_url": "https://www.binance.com/bapi/...",
  "source_detail_url": "https://www.binance.com/en/support/announcement/...",
  "source_domain": "binance.com",
  "title": "...",
  "event_type": "futures_contract_launch",
  "source_published_at_ms": 1782185438167,
  "event_time_ms": 1782185438167,
  "available_at_ms": 1782185438167 + 15m,
  "available_at_policy": "source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
  "symbols": ["ARX"],
  "symbol_count": 1,
  "manual_review_status": "reviewed_high_confidence",
  "input_payload_hash": "sha256(canonical_input_row)",
  "article_payload_hash": "sha256(canonical_article_row)",
  "notice_time_ms": 1782185438167,
  "effective_time_ms": null,
  "effective_time_parse_status": "not_parsed_in_stage1_5b",
  "directional_hypothesis": "undefined",
  "signed_direction": null,
  "long_allowed": false,
  "short_allowed": false,
  "replay_allowed": false,
  "stage1_5c_review_pending": true,
  "stage1_5c_input_allowed": true,
  "stage1_5c_replay_candidate_allowed": false,
  "stage1_5c_requires_price_coverage_check": true,
  "stage1_5c_requires_filter_group_assignment": true,
  "stage1_5c_requires_baseline_evaluation": true
}
```

### 2.2 Normalized symbol-event row schema

Each row in `external_catalyst_events_normalized.jsonl` must include:

```json
{
  "symbol_event_id": "sha256(article_event_id|symbol)",
  "article_event_id": "...",
  "event_type": "exchange_delisting_notice",
  "symbol": "COSUSDT",
  "base_asset": "COS",
  "quote_asset": "USDT",
  "venue": "binance",
  "source_name": "binance_official_announcements",
  "source_profile": "binance_official_announcements_like_rows",
  "source_detail_url": "https://www.binance.com/en/support/announcement/...",
  "source_parent_url": "https://www.binance.com/bapi/...",
  "title": "...",
  "source_published_at_ms": 1780642807472,
  "event_time_ms": 1780642807472,
  "notice_time_ms": 1780642807472,
  "effective_time_ms": null,
  "effective_time_parse_status": "not_parsed_in_stage1_5b",
  "available_at_ms": 1780642807472 + 15m,
  "available_at_policy": "source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
  "event_payload_hash": "sha256(canonical_symbol_event_row)",
  "source_quality": "stage1_5a_passed_manual_reviewed_high_confidence",
  "source_audit_decision": "source_audit_passed",
  "event_type_audit_decision": "source_audit_passed",
  "stage1_5a_source_key": "binance_official_announcements_like_rows_source",
  "stage1_5a_review_path": "docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md",
  "stage1_5a_summary_path": "data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json",
  "manual_review_status": "reviewed_high_confidence",
  "symbol_normalization_method": "base_asset_plus_usdt_assumption",
  "market_pair_existence_verified": false,
  "price_history_coverage_verified": false,
  "tradability_verified": false,
  "directional_hypothesis": "undefined",
  "signed_direction": null,
  "long_allowed": false,
  "short_allowed": false,
  "context_labels_allowed": false,
  "replay_allowed": false,
  "stage1_5c_review_pending": true,
  "stage1_5c_input_allowed": true,
  "stage1_5c_replay_candidate_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false
}
```

### 2.3 Symbol normalization rule

Input symbols are base assets such as `ARX`, `COS`, `HIGH`.

Normalize as:

```text
base_asset = input symbol uppercased
symbol = base_asset + "USDT"
quote_asset = USDT
```

This is only a research symbol convention. It must not imply that Binance has an active spot/perp `BASEUSDT` market or sufficient price history. Every normalized row must carry:

```json
{
  "symbol_normalization_method": "base_asset_plus_usdt_assumption",
  "market_pair_existence_verified": false,
  "price_history_coverage_verified": false,
  "tradability_verified": false
}
```

Stage 1.5C must perform price coverage, tradability, liquidity and depth checks before replay.

Reject / quarantine symbol if:

```text
contains "/"
empty
not matching ^[A-Z0-9]{2,15}$
in explicit forbidden symbolic words list
```

First version must not support non-USDT quote assets. Fiat pairs and bStocks/TradFi were already rejected in manual review and must remain out of scope.

---

## 3. Decision Gates

### 3.1 Build pass

`stage1_5b_event_table_ready` requires:

```text
source_audit_summary.overall_decision == source_audit_passed
source_audit_summary.research_result_valid == true
at least one source_decision == source_audit_passed
article_level_row_count >= 30
normalized_symbol_event_count >= 30
unique_event_days >= 20
symbols_with_events >= 3
allowed_event_type_rows_only == true
manual_review_status_pass_rate == 100%
source_detail_url_present_rate == 100%
source_published_at_present_rate == 100%
symbol_normalization_quarantine_count == 0
article_event_id_duplicate_count == 0
symbol_event_id_duplicate_count == 0
```

### 3.2 Build sparse / failed

`stage1_5b_event_table_sparse_inconclusive` if source audit passed but article rows are below 30, unique event days below 20, or symbols below 3.

Do not fail solely because `article_level_row_count > 100`. The value 100 is only a first-version target size for a minimal hand-audited table; more high-confidence reviewed articles are not a safety failure.

`stage1_5b_event_table_failed` if any hard safety gate fails:

```text
source audit not passed
research_result_valid != true
unsupported event type present
forbidden payload key present
manual_review_status != reviewed_high_confidence
missing source detail URL
missing timestamp
symbol quarantine count > 0
duplicate event IDs > 0
```

### 3.3 Review next action

If ready:

```text
next_action = write_stage1_5c_external_catalyst_replay_implementation_plan
```

This next action only allows writing the Stage 1.5C plan. It does not mean any Stage 1.5B row is a replay candidate. Stage 1.5C must independently check price coverage, tradability, liquidity, filter-group assignment and baseline/replay rules.

If sparse:

```text
next_action = collect_more_high_confidence_events_or_add_okx_source_audit
```

If failed:

```text
next_action = fix_event_table_inputs_before_replay
```

---

## 4. Implementation Tasks

## Task 1: Add Stage 1.5B Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5b_event_table_config.py`

**Step 1: Write failing config test**

Create `tests/research/external_signal_shadow/test_stage1_5b_event_table_config.py`:

```python
from configs import base


def test_stage1_5b_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_ARTICLE_EVENTS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_TARGET_MAX_ARTICLE_EVENTS_FIRST_PASS == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_UNIQUE_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_PRIMARY_ANNOUNCEMENT_DELAY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES == (
        "exchange_delisting_notice",
        "futures_contract_launch",
    )
    assert "margin_enablement" not in base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_config.py -q
```

Expected: fail because constants do not exist.

**Step 3: Add constants**

Append to `configs/base.py`:

```python
# ─── External Signal Shadow Lab Stage 1.5B: Minimal Historical Event Table ────

EXTERNAL_SIGNAL_STAGE1_5B_MIN_ARTICLE_EVENTS = 30
# Minimum manually reviewed article-level events required for event table readiness.

EXTERNAL_SIGNAL_STAGE1_5B_TARGET_MAX_ARTICLE_EVENTS_FIRST_PASS = 100
# Target maximum for first-pass manual review scope only. This is not a hard failure gate.

EXTERNAL_SIGNAL_STAGE1_5B_MIN_UNIQUE_EVENT_DAYS = 20
# Minimum UTC event days required for source diversity.

EXTERNAL_SIGNAL_STAGE1_5B_MIN_SYMBOLS_WITH_EVENTS = 3
# Minimum unique normalized symbols required.

EXTERNAL_SIGNAL_STAGE1_5B_PRIMARY_ANNOUNCEMENT_DELAY_MS = 15 * 60 * 1000
# Conservative available_at lag inherited from Stage 1.5A.

EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES = (
    "exchange_delisting_notice",
    "futures_contract_launch",
)
# Only Stage 1.5A-passed event types may enter Stage 1.5B.

EXTERNAL_SIGNAL_STAGE1_5B_SOURCE_PROFILE = "binance_official_announcements_like_rows"
# Source profile for the current Binance official announcements table.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_config.py -q
```

Expected: pass.

---

## Task 2: Add Event Table Models

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5b_event_table_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5b_event_table_models.py`

**Step 1: Write failing model tests**

```python
from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    EventTableDecision,
    SymbolEventRow,
)


def test_stage1_5b_models_have_required_safety_flags():
    article = ArticleEventRow(
        article_event_id="a1",
        stage1_5a_source_line=1,
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        source_capture_method="semi_auto_collector",
        source_url="https://www.binance.com/bapi/x",
        source_detail_url="https://www.binance.com/en/support/announcement/x",
        source_domain="binance.com",
        title="Binance Will Delist ABC",
        event_type="exchange_delisting_notice",
        source_published_at_ms=1710921600000,
        event_time_ms=1710921600000,
        available_at_ms=1710922500000,
        available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
        symbols=["ABC"],
        symbol_count=1,
        manual_review_status="reviewed_high_confidence",
        input_payload_hash="h1",
        article_payload_hash="h2",
        notice_time_ms=1710921600000,
        effective_time_ms=None,
        effective_time_parse_status="not_parsed_in_stage1_5b",
        directional_hypothesis="undefined",
        signed_direction=None,
        long_allowed=False,
        short_allowed=False,
        replay_allowed=False,
        stage1_5c_review_pending=True,
        stage1_5c_input_allowed=True,
        stage1_5c_replay_candidate_allowed=False,
        stage1_5c_requires_price_coverage_check=True,
        stage1_5c_requires_filter_group_assignment=True,
        stage1_5c_requires_baseline_evaluation=True,
    )
    assert article.replay_allowed is False
    assert article.stage1_5c_review_pending is True
    assert article.stage1_5c_replay_candidate_allowed is False
    assert article.directional_hypothesis == "undefined"
    assert article.signed_direction is None


def test_symbol_event_row_disallows_trading_execution():
    row = SymbolEventRow(
        symbol_event_id="s1",
        article_event_id="a1",
        event_type="futures_contract_launch",
        symbol="ABCUSDT",
        base_asset="ABC",
        quote_asset="USDT",
        venue="binance",
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        source_detail_url="https://www.binance.com/en/support/announcement/x",
        source_parent_url="https://www.binance.com/bapi/x",
        title="Binance Futures Will Launch ABCUSDT",
        source_published_at_ms=1710921600000,
        event_time_ms=1710921600000,
        available_at_ms=1710922500000,
        available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
        notice_time_ms=1710921600000,
        effective_time_ms=None,
        effective_time_parse_status="not_parsed_in_stage1_5b",
        event_payload_hash="h",
        source_quality="stage1_5a_passed_manual_reviewed_high_confidence",
        source_audit_decision="source_audit_passed",
        event_type_audit_decision="source_audit_passed",
        stage1_5a_source_key="binance_official_announcements_like_rows_source",
        stage1_5a_review_path="docs/reviews/stage1_5a_review.md",
        stage1_5a_summary_path="data/external_signal_shadow/stage1_5a/summary.json",
        manual_review_status="reviewed_high_confidence",
        symbol_normalization_method="base_asset_plus_usdt_assumption",
        market_pair_existence_verified=False,
        price_history_coverage_verified=False,
        tradability_verified=False,
        directional_hypothesis="undefined",
        signed_direction=None,
        long_allowed=False,
        short_allowed=False,
        context_labels_allowed=False,
        replay_allowed=False,
        stage1_5c_review_pending=True,
        stage1_5c_input_allowed=True,
        stage1_5c_replay_candidate_allowed=False,
        paper_trading_allowed=False,
        live_trading_allowed=False,
    )
    assert row.paper_trading_allowed is False
    assert row.live_trading_allowed is False
    assert row.market_pair_existence_verified is False
    assert row.price_history_coverage_verified is False
    assert row.tradability_verified is False
    assert row.directional_hypothesis == "undefined"
    assert row.signed_direction is None
    assert row.stage1_5c_replay_candidate_allowed is False


def test_event_table_decision_enum_values():
    assert EventTableDecision.READY.value == "stage1_5b_event_table_ready"
    assert EventTableDecision.SPARSE.value == "stage1_5b_event_table_sparse_inconclusive"
    assert EventTableDecision.FAILED.value == "stage1_5b_event_table_failed"
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_models.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement dataclasses and enum**

Use `@dataclass` for `ArticleEventRow`, `SymbolEventRow`; use `Enum` for `EventTableDecision`.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_models.py -q
```

Expected: pass.

---

## Task 3: Add Loader and Upstream Audit Gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5b_event_table_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5b_event_table_loader.py`

**Step 1: Write failing loader tests**

```python
import json

import pytest

from src.research.external_signal_shadow.stage1_5b_event_table_loader import (
    assert_stage1_5a_audit_passed,
    load_high_confidence_candidate_rows,
)


def test_load_high_confidence_candidate_rows_rejects_non_reviewed_rows(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_status": "review_rejected",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT",
        "url": "https://www.binance.com/en/support/announcement/x",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="manual_review_status"):
        load_high_confidence_candidate_rows(path)


def test_load_rejects_row_missing_time_field(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "symbol": ["ABC"],
        "title": "Binance Futures Will Launch ABCUSDT",
        "url": "https://www.binance.com/en/support/announcement/x",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="time"):
        load_high_confidence_candidate_rows(path)


def test_load_rejects_row_missing_url_field(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="url"):
        load_high_confidence_candidate_rows(path)


def test_assert_stage1_5a_audit_passed_rejects_sparse_summary(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_sparse_inconclusive",
        "research_result_valid": True,
        "source_decisions": {},
        "event_type_decisions": {},
    }))

    with pytest.raises(ValueError, match="source_audit_passed"):
        assert_stage1_5a_audit_passed(summary)


def test_assert_stage1_5a_audit_passed_returns_allowed_event_types(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": [
                    "exchange_delisting_notice",
                    "futures_contract_launch",
                ],
            }
        },
        "event_type_decisions": {
            "exchange_delisting_notice": "source_audit_passed",
            "futures_contract_launch": "source_audit_passed",
            "margin_enablement": "source_audit_sparse_inconclusive",
        },
    }))

    allowed = assert_stage1_5a_audit_passed(summary)
    assert allowed == {"exchange_delisting_notice", "futures_contract_launch"}


def test_allowed_event_types_are_intersection_of_config_and_stage1_5a_recommendations(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": [
                    "futures_contract_launch",
                    "margin_enablement",
                ],
            }
        },
        "event_type_decisions": {
            "futures_contract_launch": "source_audit_passed",
            "margin_enablement": "source_audit_passed",
        },
    }))

    allowed = assert_stage1_5a_audit_passed(summary)
    assert allowed == {"futures_contract_launch"}
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_loader.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement loader**

Implement:

```python
def load_high_confidence_candidate_rows(path: str | Path) -> list[dict]:
    ...

def assert_stage1_5a_audit_passed(summary_path: str | Path) -> set[str]:
    ...
```

Rules:

```text
allowed_event_types = (
  configs/base.py EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES
  ∩ Stage 1.5A source_decision.recommended_event_types_for_stage1_5b
  ∩ Stage 1.5A event_type_decisions where decision == source_audit_passed
)

manual_review_status must equal reviewed_high_confidence
manual_review_required must be true
source_name must equal binance_official_announcements
url/source_url/title/time/symbol must exist
no forbidden payload keys
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_loader.py -q
```

Expected: pass.

---

## Task 4: Add Normalizer / Expander

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5b_event_table_normalizer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5b_event_table_normalizer.py`

**Step 1: Write failing normalizer tests**

```python
from src.research.external_signal_shadow.stage1_5b_event_table_normalizer import (
    build_article_event_rows,
    expand_symbol_event_rows,
    normalize_base_asset_symbol,
)


def test_normalize_base_asset_symbol_to_usdt_pair():
    assert normalize_base_asset_symbol("abc") == ("ABC", "ABCUSDT", "USDT")


def test_normalize_rejects_ambiguous_symbol():
    try:
        normalize_base_asset_symbol("PEPE/WBTC/USDT")
    except ValueError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_build_article_and_symbol_rows_expand_multi_symbol_event():
    rows = [{
        "event_type_candidate": "exchange_delisting_notice",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 35,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["COS", "HIGH", "MBOX"],
        "time": 1780642807472,
        "title": "Binance Will Delist COS, D, HIGH, MBOX on 2026-06-19",
        "url": "https://www.binance.com/en/support/announcement/x",
    }]

    article_rows = build_article_event_rows(rows, allowed_event_types={"exchange_delisting_notice"})
    symbol_rows = expand_symbol_event_rows(article_rows, source_audit_decisions={
        "exchange_delisting_notice": "source_audit_passed"
    })

    assert len(article_rows) == 1
    assert article_rows[0].symbol_count == 3
    assert len(symbol_rows) == 3
    assert {r.symbol for r in symbol_rows} == {"COSUSDT", "HIGHUSDT", "MBOXUSDT"}
    assert all(r.replay_allowed is False for r in symbol_rows)
    assert all(r.context_labels_allowed is False for r in symbol_rows)
    assert all(r.directional_hypothesis == "undefined" for r in symbol_rows)
    assert all(r.signed_direction is None for r in symbol_rows)
    assert all(r.effective_time_ms is None for r in symbol_rows)
    assert all(r.effective_time_parse_status == "not_parsed_in_stage1_5b" for r in symbol_rows)
    assert all(r.market_pair_existence_verified is False for r in symbol_rows)
    assert all(r.price_history_coverage_verified is False for r in symbol_rows)
    assert all(r.tradability_verified is False for r in symbol_rows)
    for row in symbol_rows:
        assert not hasattr(row, "local_forceorder_context_present")
        assert not hasattr(row, "funding_context_present")
        assert not hasattr(row, "oi_context_present")
        assert not hasattr(row, "btc_regime_context_present")
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_normalizer.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement normalizer**

Required functions:

```python
def canonical_json_hash(obj: dict) -> str:
    ...

def normalize_base_asset_symbol(raw_symbol: str) -> tuple[str, str, str]:
    ...

def build_article_event_rows(rows: list[dict], allowed_event_types: set[str]) -> list[ArticleEventRow]:
    ...

def expand_symbol_event_rows(article_rows: list[ArticleEventRow], source_audit_decisions: dict[str, str]) -> list[SymbolEventRow]:
    ...

def dataclass_to_json_dict(row) -> dict:
    ...
```

Hashing rules:

```text
input_payload_hash = sha256(canonical input row)
article_event_id = sha256(title|time|url)
article_payload_hash = sha256(canonical article row excluding article_payload_hash)
symbol_event_id = sha256(article_event_id|symbol)
event_payload_hash = sha256(canonical symbol event row excluding event_payload_hash)
```

Available-at rule:

```text
available_at_ms = source_published_at_ms + EXTERNAL_SIGNAL_STAGE1_5B_PRIMARY_ANNOUNCEMENT_DELAY_MS
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_normalizer.py -q
```

Expected: pass.

---

## Task 5: Add Quality Summary Engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5b_event_table_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5b_event_table_summary.py`

**Step 1: Write failing summary tests**

```python
from src.research.external_signal_shadow.stage1_5b_event_table_models import EventTableDecision
from src.research.external_signal_shadow.stage1_5b_event_table_summary import build_event_table_summary


import pytest

from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    EventTableDecision,
    SymbolEventRow,
)
from src.research.external_signal_shadow.stage1_5b_event_table_summary import build_event_table_summary


@pytest.fixture
def sample_article_rows():
    rows = []
    base_ts = 1710000000000
    for i in range(30):
        ts = base_ts + i * 86_400_000
        rows.append(ArticleEventRow(
            article_event_id=f"article-{i}",
            stage1_5a_source_line=i + 1,
            source_name="binance_official_announcements",
            source_profile="binance_official_announcements_like_rows",
            source_capture_method="semi_auto_collector",
            source_url="https://www.binance.com/bapi/x",
            source_detail_url=f"https://www.binance.com/en/support/announcement/{i}",
            source_domain="binance.com",
            title=f"Binance Futures Will Launch TOK{i:02d}USDT Perpetual Contract",
            event_type="futures_contract_launch" if i < 20 else "exchange_delisting_notice",
            source_published_at_ms=ts,
            event_time_ms=ts,
            notice_time_ms=ts,
            effective_time_ms=None,
            effective_time_parse_status="not_parsed_in_stage1_5b",
            available_at_ms=ts + 900_000,
            available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
            symbols=[f"TOK{i:02d}"],
            symbol_count=1,
            manual_review_status="reviewed_high_confidence",
            input_payload_hash=f"input-{i}",
            article_payload_hash=f"article-hash-{i}",
            directional_hypothesis="undefined",
            signed_direction=None,
            long_allowed=False,
            short_allowed=False,
            replay_allowed=False,
            stage1_5c_review_pending=True,
            stage1_5c_input_allowed=True,
            stage1_5c_replay_candidate_allowed=False,
            stage1_5c_requires_price_coverage_check=True,
            stage1_5c_requires_filter_group_assignment=True,
            stage1_5c_requires_baseline_evaluation=True,
        ))
    return rows


@pytest.fixture
def sample_symbol_rows(sample_article_rows):
    rows = []
    for article in sample_article_rows:
        base_asset = article.symbols[0]
        rows.append(SymbolEventRow(
            symbol_event_id=f"symbol-{article.article_event_id}",
            article_event_id=article.article_event_id,
            event_type=article.event_type,
            symbol=f"{base_asset}USDT",
            base_asset=base_asset,
            quote_asset="USDT",
            venue="binance",
            source_name=article.source_name,
            source_profile=article.source_profile,
            source_detail_url=article.source_detail_url,
            source_parent_url=article.source_url,
            title=article.title,
            source_published_at_ms=article.source_published_at_ms,
            event_time_ms=article.event_time_ms,
            notice_time_ms=article.notice_time_ms,
            effective_time_ms=None,
            effective_time_parse_status="not_parsed_in_stage1_5b",
            available_at_ms=article.available_at_ms,
            available_at_policy=article.available_at_policy,
            event_payload_hash=f"event-{article.article_event_id}",
            source_quality="stage1_5a_passed_manual_reviewed_high_confidence",
            source_audit_decision="source_audit_passed",
            event_type_audit_decision="source_audit_passed",
            stage1_5a_source_key="binance_official_announcements_like_rows_source",
            stage1_5a_review_path="docs/reviews/stage1_5a_review.md",
            stage1_5a_summary_path="data/external_signal_shadow/stage1_5a/summary.json",
            manual_review_status="reviewed_high_confidence",
            symbol_normalization_method="base_asset_plus_usdt_assumption",
            market_pair_existence_verified=False,
            price_history_coverage_verified=False,
            tradability_verified=False,
            directional_hypothesis="undefined",
            signed_direction=None,
            long_allowed=False,
            short_allowed=False,
            context_labels_allowed=False,
            replay_allowed=False,
            stage1_5c_review_pending=True,
            stage1_5c_input_allowed=True,
            stage1_5c_replay_candidate_allowed=False,
            paper_trading_allowed=False,
            live_trading_allowed=False,
        ))
    return rows


def test_summary_ready_when_article_and_symbol_density_pass(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=True)
    assert summary["decision"] == EventTableDecision.READY.value
    assert summary["article_level_row_count"] >= 30
    assert summary["replay_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["stage1_5c_candidate_allowance_not_determined_by_stage1_5b"] is True
    assert summary["next_action"] == "write_stage1_5c_external_catalyst_replay_implementation_plan"


def test_summary_reports_event_type_counts_article_and_symbol_level(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=True)
    assert summary["event_type_counts_article_level"] == {
        "futures_contract_launch": 20,
        "exchange_delisting_notice": 10,
    }
    assert summary["event_type_counts_symbol_level"] == {
        "futures_contract_launch": 20,
        "exchange_delisting_notice": 10,
    }


def test_summary_failed_when_source_audit_not_passed(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=False)
    assert summary["decision"] == EventTableDecision.FAILED.value
    assert "source_audit_not_passed" in summary["blockers"]
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_summary.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement summary**

Output must include:

```json
{
  "stage": "external_signal_shadow_lab_stage1_5b",
  "scope": "minimal_historical_event_table_only",
  "decision": "stage1_5b_event_table_ready|stage1_5b_event_table_sparse_inconclusive|stage1_5b_event_table_failed",
  "source_audit_required": true,
  "source_audit_passed_required": true,
  "source_audit_passed": true,
  "article_level_row_count": 94,
  "normalized_symbol_event_count": 194,
  "unique_event_days": 81,
  "symbols_with_events": 191,
  "event_type_counts_article_level": {},
  "event_type_counts_symbol_level": {},
  "multi_symbol_article_count": 40,
  "source_detail_url_present_rate": 1.0,
  "source_published_at_present_rate": 1.0,
  "manual_review_status_pass_rate": 1.0,
  "article_event_id_duplicate_count": 0,
  "symbol_event_id_duplicate_count": 0,
  "symbol_normalization_quarantine_count": 0,
  "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": true,
  "stage1_5c_review_pending": true,
  "stage1_5c_replay_candidate_allowed": false,
  "context_label_join_allowed": false,
  "blockers": [],
  "next_action": "write_stage1_5c_external_catalyst_replay_implementation_plan",
  "price_join_allowed": false,
  "forward_return_allowed": false,
  "replay_allowed": false,
  "alpha_interpretation_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false
}
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5b_event_table_summary.py -q
```

Expected: pass.

---

## Task 6: Add Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5b_minimal_historical_event_table.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5b_minimal_historical_event_table.py`

**Step 1: Write failing runner test**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5b_minimal_historical_event_table import main


def test_runner_writes_raw_normalized_and_summary(tmp_path):
    input_jsonl = tmp_path / "high_confidence.jsonl"
    audit_summary = tmp_path / "stage1_5a_summary.json"
    raw_out = tmp_path / "raw.jsonl"
    norm_out = tmp_path / "normalized.jsonl"
    summary_out = tmp_path / "summary.json"

    input_jsonl.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 1,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT Perpetual Contract",
        "url": "https://www.binance.com/en/support/announcement/x",
    }) + "\n")
    audit_summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": ["futures_contract_launch"],
            }
        },
        "event_type_decisions": {"futures_contract_launch": "source_audit_passed"},
    }))

    args = [
        "run_stage1_5b_minimal_historical_event_table.py",
        "--input-jsonl", str(input_jsonl),
        "--stage1-5a-summary", str(audit_summary),
        "--output-raw-jsonl", str(raw_out),
        "--output-normalized-jsonl", str(norm_out),
        "--output-summary", str(summary_out),
    ]
    with patch("sys.argv", args):
        main()

    assert raw_out.exists()
    assert norm_out.exists()
    assert summary_out.exists()
    normalized = [json.loads(line) for line in norm_out.read_text().splitlines()]
    assert normalized[0]["symbol"] == "ABCUSDT"
    assert normalized[0]["replay_allowed"] is False
    assert normalized[0]["stage1_5c_review_pending"] is True
    assert normalized[0]["stage1_5c_replay_candidate_allowed"] is False
    assert normalized[0]["market_pair_existence_verified"] is False
    assert normalized[0]["price_history_coverage_verified"] is False
    assert normalized[0]["tradability_verified"] is False
    assert normalized[0]["directional_hypothesis"] == "undefined"
    assert normalized[0]["signed_direction"] is None
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5b_minimal_historical_event_table.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement runner**

CLI:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5b_minimal_historical_event_table.py \
  --input-jsonl data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_reviewed_high_confidence.jsonl \
  --stage1-5a-summary data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json \
  --output-raw-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl \
  --output-normalized-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --output-summary data/external_signal_shadow/stage1_5b/normalization_summary.json
```

Implementation sequence:

```text
load rows
assert Stage 1.5A passed
build article rows
expand symbol rows
build summary
write raw JSONL
write normalized JSONL
write summary JSON
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5b_minimal_historical_event_table.py -q
```

Expected: pass.

---

## Task 7: Add Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5b_minimal_historical_event_table.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5b_minimal_historical_event_table.py`

**Step 1: Write failing review test**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5b_minimal_historical_event_table import main


def test_review_writes_markdown_and_states_no_replay(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "source_audit_passed": True,
        "article_level_row_count": 94,
        "normalized_symbol_event_count": 194,
        "unique_event_days": 81,
        "symbols_with_events": 191,
        "event_type_counts_article_level": {
            "futures_contract_launch": 71,
            "exchange_delisting_notice": 23,
        },
        "event_type_counts_symbol_level": {},
        "blockers": [],
        "next_action": "write_stage1_5c_external_catalyst_replay_implementation_plan",
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": True,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "context_label_join_allowed": False,
    }))

    args = [
        "review_stage1_5b_minimal_historical_event_table.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()

    content = review.read_text()
    assert "Stage 1.5B" in content
    assert "stage1_5b_event_table_ready" in content
    assert "replay_allowed" in content
    assert "stage1_5c_replay_candidate_allowed" in content
    assert "market pair" in content or "tradability" in content
    assert "directional_hypothesis" in content
    assert "context_label_join_allowed" in content
    assert "write_stage1_5c_external_catalyst_replay_implementation_plan" in content
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5b_minimal_historical_event_table.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement review script**

Sections:

```text
结论
Input / Output Evidence
Article-level Coverage
Symbol-expanded Coverage
Event Type Counts
Safety Boundaries
Blockers
Allowed Next Action
```

Review must explicitly say:

```text
Stage 1.5B ready does not mean alpha exists.
Stage 1.5B ready does not allow paper/live.
Stage 1.5B ready does not determine Stage 1.5C replay candidate allowance.
Stage 1.5B ready only permits writing Stage 1.5C replay implementation plan.
BASEUSDT normalized symbols are research assumptions only; market pair existence, price coverage, tradability, liquidity and depth remain unverified until Stage 1.5C.
Directional hypothesis is undefined; long/short direction and execution intent are not allowed.
Funding/OI/liquidation/BTC regime context labels are not emitted in Stage 1.5B.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5b_minimal_historical_event_table.py -q
```

Expected: pass.

---

## Task 8: End-to-End Real Artifact Smoke

**Files:**
- Input: `data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_reviewed_high_confidence.jsonl`
- Input: `data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json`
- Output: `data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl`
- Output: `data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl`
- Output: `data/external_signal_shadow/stage1_5b/normalization_summary.json`
- Output: `docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md`

**Step 1: Run event table builder**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5b_minimal_historical_event_table.py \
  --input-jsonl data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_reviewed_high_confidence.jsonl \
  --stage1-5a-summary data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json \
  --output-raw-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl \
  --output-normalized-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --output-summary data/external_signal_shadow/stage1_5b/normalization_summary.json
```

Expected:

```text
article_level_row_count = 94
normalized_symbol_event_count = 194
decision = stage1_5b_event_table_ready
```

**Step 2: Generate review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5b_minimal_historical_event_table.py \
  --summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --output-review docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md
```

Expected: review states event table ready, but replay/paper/live/alpha disabled.
Expected: review also states Stage 1.5C replay candidate allowance is not determined by Stage 1.5B, symbols are market/tradability-unverified, direction is undefined, and context labels are not joined.

**Step 3: Inspect key fields**

```bash
uv run python - <<'PY'
import json
with open('data/external_signal_shadow/stage1_5b/normalization_summary.json', encoding='utf-8') as f:
    s = json.load(f)
print(json.dumps({
    'decision': s['decision'],
    'article_level_row_count': s['article_level_row_count'],
    'normalized_symbol_event_count': s['normalized_symbol_event_count'],
    'unique_event_days': s['unique_event_days'],
    'symbols_with_events': s['symbols_with_events'],
    'replay_allowed': s['replay_allowed'],
    'stage1_5c_replay_candidate_allowed': s['stage1_5c_replay_candidate_allowed'],
    'stage1_5c_candidate_allowance_not_determined_by_stage1_5b': s['stage1_5c_candidate_allowance_not_determined_by_stage1_5b'],
    'next_action': s['next_action'],
}, ensure_ascii=False, indent=2))
PY
```

Expected:

```json
{
  "decision": "stage1_5b_event_table_ready",
  "article_level_row_count": 94,
  "normalized_symbol_event_count": 194,
  "unique_event_days": 81,
  "symbols_with_events": 191,
  "replay_allowed": false,
  "stage1_5c_replay_candidate_allowed": false,
  "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": true,
  "next_action": "write_stage1_5c_external_catalyst_replay_implementation_plan"
}
```

---

## 5. Verification Commands

Run all Stage 1.5B tests:

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

Run compatibility tests touching Stage 1.5A handoff:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py \
  tests/scripts/external_signal_shadow/test_collect_stage1_5a_external_catalyst_events.py \
  -q
```

Run ruff:

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5b_event_table_*.py \
  scripts/external_signal_shadow/*stage1_5b* \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_*.py \
  tests/scripts/external_signal_shadow/*stage1_5b*
```

Check generated artifacts:

```bash
wc -l \
  data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl \
  data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl
```

Expected approximately:

```text
94 external_catalyst_events_raw.jsonl
194 external_catalyst_events_normalized.jsonl
```

---

## 6. Non-Goals / Guardrails

Do not add any of the following in Stage 1.5B:

```text
price loading
forward return calculation
entry/exit rules
random baseline
slippage/cost model
filter matrix replay groups
funding/OI/liquidation context labels
paper/live trading flags set to true
```

If any reviewer asks to add replay to 1.5B, reject and defer to Stage 1.5C.

If any reviewer asks to include `margin_enablement` or `trading_pair_addition_for_existing_liquid_asset`, reject unless Stage 1.5A source audit and manual review are rerun and those event types pass independently.

---

## 7. Git / Artifact Hygiene

Before any commit, verify whether generated data artifacts are ignored:

```bash
git check-ignore -v data/external_signal_shadow/stage1_5b/external_catalyst_events_raw.jsonl || true
git check-ignore -v data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl || true
git check-ignore -v data/external_signal_shadow/stage1_5b/normalization_summary.json || true
```

Policy:

```text
data/external_signal_shadow/stage1_5b/*.jsonl should not be committed by default
docs/reviews/** can be committed as decision artifacts
normalization_summary.json can be committed only if the project has already accepted Stage 1.5 summary JSON artifacts; otherwise keep it local and commit the review only
```

If data files are not ignored, ask the user before editing `.gitignore`. Do not silently commit generated JSONL data.

## 8. Expected Final Status

After implementation and smoke run, expected result:

```text
Stage 1.5B event table ready
Binance source/event table can proceed to Stage 1.5C replay plan writing and independent 1.5C loader/review checks
No Stage 1.5C replay candidate allowance determined by 1.5B
No alpha claim allowed
No paper/live allowed
No execution intent allowed
```

Do not commit automatically. End with:

```bash
git status --short
```

and list changed files for user review.
