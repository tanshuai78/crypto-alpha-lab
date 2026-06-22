# External Signal Shadow Lab Stage 1.5A Historical Event Source Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现 `Stage 1.5A Historical Event Source Audit`，只审计 external catalyst source 的历史可得性、字段质量、时间戳质量、symbol mapping 和 connector resource safety，不做 replay、不做 live smoke、不输出 alpha / paper / live 结论。

**Architecture:** 新增独立 `stage1_5a_source_audit_*` 模块，按 `Layer A / Layer B` 执行 source audit：先做 bounded fetch / local fixture load，再做 source resource safety、forbidden payload、timestamp quality、event type / magnitude / symbol mapping 审计，最后输出 JSON summary 与中文 review。所有阈值进入 `configs/base.py`；测试使用本地 fixture，真实联网 source audit 只能由 runner 显式执行。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、JSON/JSONL/HTML 文本解析、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行前边界

```text
decision = approved_with_major_required_fixes
scope = historical_event_source_audit_only
replay_allowed = false
live_smoke_allowed = false
alpha_interpretation_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

Coding 前必须吸收以下修正：

1. 增加 Binance / OKX 最小 HTML/index extraction profile；不能让真实 HTML source 只产出 `normalized_event_count = 0` 后滑入 sparse。
2. Summary 必须输出 `overall_decision`、`source_decisions`、`event_type_decisions`，不能只做全局 decision。
3. Event type 必须分层：`eligible_for_stage1_5b` vs `observation_only_in_stage1_5a`。
4. Domain allowlist 必须防 suffix spoofing，并在 redirect 后重验最终域名。
5. `available_at_ms` 必须按 source type 区分；unlock calendar 无 historical snapshot 时只能 observation-only。
6. 必须定义 `source_url` / `source_parent_url` / `raw_payload_hash` / `event_payload_hash` 粒度。
7. 必须拆分 `base_asset_mapping_pass_rate` 与 `trade_pair_mapping_pass_rate`。
8. 真实联网 audit 必须写 raw cache，并标记 `network_result_not_deterministic = true`。
9. 真实运行建议必须给出 source audit matrix，而不是笼统写 Binance / OKX / unlocks。

本计划只实现：

```text
stage1_5a_historical_event_source_audit_only
```

允许实现：

```text
Layer A: source_integrity / forbidden_payload / source_resource_safety / available_at / hindsight
Layer B: event_type / magnitude / historical availability
source_audit_summary.json
source_audit_review_CN.md
```

禁止实现：

```text
Layer C context labels
Layer D replay groups
historical replay
forward return
random baseline
live smoke collector
paper trading
live trading
TradeIntent
position sizing
```

Summary 顶层必须固定：

```json
{
  "stage": "external_signal_shadow_lab_stage1_5a",
  "scope": "historical_event_source_audit_only",
  "execution_engine_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "historical_replay_allowed": false,
  "live_smoke_allowed": false,
  "source_resource_safety_required": true,
  "event_type_mixing_allowed_for_replay_pass": false,
  "post_hoc_group_selection_allowed": false,
  "overall_decision": "source_audit_passed|source_audit_sparse_inconclusive|source_audit_failed",
  "source_decisions_required": true,
  "event_type_decisions_required": true
}
```

执行规则：

- 所有测试命令统一使用 `PYTHONPATH=src:.`。
- 本计划不包含任何自动 `git commit`。每个任务结束后最多执行 `git status --short`，由用户决定是否提交。
- 测试不得访问互联网。联网 source audit 只能在 runner 手动执行时发生。
- 如果真实 source 格式变化，必须 quarantine，不得 silent fallback，不得自动猜 symbol。
- HTML / index source 如果没有 parser profile 或 parser profile 产出 0 个 normalized event，必须记为 `source_format_drift_count += 1`，对应 source decision 强制 `source_audit_failed`。
- 真实联网运行必须写 raw cache；raw cache 是本地审计证据，默认不得提交 Git。

---

## 1. 设计输入

必须继承以下文档：

- `docs/strategy_specs/2026-06-21-external-signal-shadow-lab-external-catalyst-events-filter-branch-brief_CN.md`
- `docs/designs/2026-06-21-external-signal-shadow-lab-stage1-5-external-catalyst-architecture-design_CN.md`
- `docs/designs/2026-06-22-external-signal-shadow-lab-stage1-5-external-catalyst-filter-matrix-design_CN.md`

Stage 1.5A 只实现 filter matrix 中：

```text
Layer A: Hard Veto Filters
Layer B: Eligibility Filters
```

不得实现：

```text
Layer C: Context Label Filters
Layer D: Replay Group Matrix
```

---

## 2. 文件结构

### 新增文件

- `src/research/external_signal_shadow/stage1_5a_source_audit_models.py`
- `src/research/external_signal_shadow/stage1_5a_source_audit_safety.py`
- `src/research/external_signal_shadow/stage1_5a_source_audit_loader.py`
- `src/research/external_signal_shadow/stage1_5a_source_audit_normalizer.py`
- `src/research/external_signal_shadow/stage1_5a_source_audit_summary.py`
- `scripts/external_signal_shadow/run_stage1_5a_historical_event_source_audit.py`
- `scripts/external_signal_shadow/review_stage1_5a_historical_event_source_audit.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_config.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_safety.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py`
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5a_historical_event_source_audit.py`

### 修改文件

- `configs/base.py`

### 输出文件

真实运行时输出到：

- `data/external_signal_shadow/stage1_5a/source_audit_summary.json`
- `docs/reviews/2026-06-22-external-signal-shadow-lab-stage1-5a-historical-event-source-audit-review_CN.md`

真实联网 fetch 还必须写 raw cache：

- `data/external_signal_shadow/stage1_5a/raw/YYYYMMDD/<source_name>/...`

raw cache 默认不提交 Git。

---

## 3. Task 1: 配置常量

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_config.py`

### Step 1: 写失败测试

测试必须覆盖：

```python
from configs import base


def test_stage1_5a_source_audit_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS
    assert "binance.com" in base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS
    assert "okx.com" in base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS

    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_PAYLOAD_BYTES > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_JSON_DEPTH >= 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_REQUEST_TIMEOUT_SEC > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_RETRY_BUDGET >= 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_EVENTS_PER_PAGE > 0

    assert base.EXTERNAL_SIGNAL_STAGE1_5A_ANNOUNCEMENT_DELAY_SCENARIOS_MS == (
        5 * 60 * 1000,
        15 * 60 * 1000,
        60 * 60 * 1000,
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_PRIMARY_ANNOUNCEMENT_DELAY_MS == 15 * 60 * 1000

    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_HISTORICAL_EVENTS_FOUND == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_PRIMARY_EVENT_TYPE_EVENTS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_UNIQUE_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_SOURCE_INTEGRITY_PASS_RATE == 0.95
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_TRADE_PAIR_MAPPING_PASS_RATE == 0.95
    assert base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_TIMESTAMP_HIGH_OR_MEDIUM_RATIO == 0.95
    assert set(base.EXTERNAL_SIGNAL_STAGE1_5A_ELIGIBLE_EVENT_TYPES_FOR_STAGE1_5B)
    assert "exchange_delisting_notice" in base.EXTERNAL_SIGNAL_STAGE1_5A_ELIGIBLE_EVENT_TYPES_FOR_STAGE1_5B
    assert "new_coin_listing" in base.EXTERNAL_SIGNAL_STAGE1_5A_OBSERVATION_ONLY_EVENT_TYPES
    assert "whale_deposit" in base.EXTERNAL_SIGNAL_STAGE1_5A_OBSERVATION_ONLY_EVENT_TYPES
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_config.py -q
```

Expected: FAIL，常量不存在。

### Step 3: 实现配置

在 `configs/base.py` 增加 `EXTERNAL_SIGNAL_STAGE1_5A_...` 常量。

建议默认值：

```text
ALLOWED_DOMAINS = ("binance.com", "www.binance.com", "okx.com", "www.okx.com", "defillama.com", "tokenomist.ai")
MAX_PAYLOAD_BYTES = 2_000_000
MAX_JSON_DEPTH = 8
REQUEST_TIMEOUT_SEC = 10
RETRY_BUDGET = 2
MAX_EVENTS_PER_PAGE = 200
```

### Step 4: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_config.py -q
git status --short
```

---

## 4. Task 2: 模型与枚举

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5a_source_audit_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py`

### Step 1: 写失败测试

覆盖：

```text
event_type enum
source profile enum
timestamp quality enum
source status enum
quarantine reason enum
summary decision enum
```

必须包含：

```text
exchange_delisting_notice
futures_contract_launch
margin_enablement
trading_pair_removal
trading_pair_addition_for_existing_liquid_asset
major_exchange_status_event
major_unlock_event
large_scheduled_token_emission
new_coin_listing
whale_deposit
```

Decision enum:

```text
source_audit_passed
source_audit_sparse_inconclusive
source_audit_failed
observation_only
```

Event type 分层必须固定：

```text
eligible_for_stage1_5b:
  exchange_delisting_notice
  futures_contract_launch
  margin_enablement
  trading_pair_removal
  trading_pair_addition_for_existing_liquid_asset
  major_exchange_status_event

observation_only_in_stage1_5a:
  major_unlock_event
  large_scheduled_token_emission
  new_coin_listing
  whale_deposit
```

### Step 2: 实现模型

建议 dataclass：

```text
RawSourcePayload
NormalizedExternalEvent
SourceAuditFinding
SourceAuditSummary
```

`NormalizedExternalEvent` 必须包含：

```text
event_id
event_type
symbol
base_asset
quote_asset
venue
source_name
source_domain
source_url
source_parent_url
source_published_at_ms
event_time_ms
available_at_ms
collector_received_at_ms
raw_payload_hash
event_payload_hash
raw_payload_size_bytes
detail_url_available
source_integrity_level
schema_version
source_timestamp_quality
historical_available_at_confidence
edited_page_risk
hindsight_risk
magnitude
base_asset_mapping_status
trade_pair_mapping_status
quarantine_reasons
replay_allowed
observation_only
```

Hash 粒度：

```text
source_url = detail article URL if available
source_parent_url = index/list URL
raw_payload_hash = detail payload hash if detail fetched else parent payload hash
event_payload_hash = hash(normalized extracted record)
detail_url_available = false 时 source_integrity_level = index_only
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py -q
git status --short
```

---

## 5. Task 3: Source Resource Safety

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5a_source_audit_safety.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_safety.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_rejects_domain_not_in_allowlist
test_rejects_evil_subdomain_spoofing
test_accepts_exact_host_or_allowed_subdomain_only
test_rejects_payload_too_large
test_rejects_json_depth_exceeded
test_detects_forbidden_payload_recursively
test_computes_raw_payload_sha256
test_quarantines_symbol_mapping_ambiguous
test_no_silent_fallback_when_schema_parse_error
```

Domain allowlist 边界测试必须覆盖：

```text
evil-binance.com -> reject
binance.com.evil.io -> reject
www.binance.com -> accept when binance.com is allowed
announcements.binance.com -> accept when binance.com is allowed
```

匹配规则必须是：

```text
host == allowed_domain
or host.endswith("." + allowed_domain)
```

禁止：

```text
allowed_domain in host
host.endswith(allowed_domain) without dot boundary
```

Forbidden payload 字段必须覆盖：

```text
api_key
secret
private_key
wallet_seed
mnemonic
authorization
bearer
access_token
refresh_token
cookie
session
csrf
password
passphrase
signed_tx
raw_tx
order_request
swap_request
transfer_request
wallet_private_key
tx_payload
```

### Step 2: 实现安全函数

建议函数：

```text
normalize_source_domain(url: str) -> str
validate_domain_allowlist(url: str, allowed_domains: tuple[str, ...]) -> SourceAuditFinding
compute_payload_sha256(payload: bytes | str) -> str
measure_json_depth(value: object) -> int
detect_forbidden_payload_keys(value: object) -> list[str]
validate_source_resource_safety(raw_payload: RawSourcePayload, config: ...) -> list[SourceAuditFinding]
```

要求：

```text
silent_fallback_allowed = false
auto_symbol_guess_allowed = false
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_safety.py -q
git status --short
```

---

## 6. Task 4: Loader / Bounded Fetch

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5a_source_audit_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_loader.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_loads_local_json_fixture
test_loads_local_jsonl_fixture
test_loads_local_html_fixture_as_text_payload
test_fetch_url_requires_allowed_domain
test_fetch_rejects_redirect_to_disallowed_domain
test_fetch_url_applies_timeout_and_retry_budget_with_mock
test_loader_records_request_timeout_count
test_loader_marks_fixture_run_true_for_local_fixture
test_network_fetch_writes_raw_cache_and_marks_not_deterministic
```

测试必须 mock HTTP，不允许真实联网。

### Step 2: 实现 loader

支持两类输入：

```text
--source-file PATH_OR_GLOB
--source-url URL
```

规则：

```text
local fixture -> fixture_run = true
source-url -> fixture_run = false
```

联网 fetch 使用标准库即可：

```text
urllib.request
timeout = EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_REQUEST_TIMEOUT_SEC
retry_budget = EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_RETRY_BUDGET
```

如果 URL domain 不在 allowlist，fetch 前直接 reject。

Redirect 规则：

```text
initial_url domain must pass allowlist
final_url after redirect must pass allowlist
redirect_to_disallowed_domain -> reject
http -> https redirect 后仍需重验最终域名
```

真实联网 fetch 必须写 raw cache：

```text
raw_cache_written = true
raw_cache_path = data/external_signal_shadow/stage1_5a/raw/YYYYMMDD/<source_name>/
network_result_not_deterministic = true
collector_received_at_ms is recorded
```

local fixture:

```text
raw_cache_written = false
network_result_not_deterministic = false
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_loader.py -q
git status --short
```

---

## 7. Task 5: Normalizer / Eligibility Audit

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5a_source_audit_normalizer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_normalizes_official_announcement_like_row
test_binance_html_profile_extracts_title_url_and_published_time_from_fixture
test_okx_html_profile_extracts_title_url_and_published_time_from_fixture
test_computes_available_at_from_source_published_plus_primary_delay
test_timestamp_source_disagreement_increments_counter
test_low_timestamp_quality_becomes_observation_only
test_unlock_without_calendar_snapshot_is_observation_only
test_new_coin_listing_is_excluded
test_whale_deposit_is_observation_only
test_existing_liquid_asset_pair_addition_can_be_eligible
test_missing_magnitude_sets_magnitude_unknown
test_ambiguous_symbol_mapping_is_quarantined
test_event_type_allowed_enum_required
test_event_hash_differs_from_parent_page_hash
test_base_asset_mapping_separate_from_trade_pair_mapping
```

### Step 2: 实现 normalizer

第一版 normalizer 接收已经被 loader 读入的 dict / JSONL rows / simple extracted records。

不要在第一版实现复杂网页 DOM 解析，但必须实现最小 HTML/index extraction profile，避免真实 Binance / OKX source 永远只得到 0 个 normalized events。

HTML / index profile 必须至少能从 fixture / fetched HTML 或 JSON-like rows 中抽出：

```text
title
source_url
source_parent_url
source_published_at_ms
event_type_candidate
raw_text
```

新增 source profile：

```text
binance_announcement_index_like_html
okx_announcement_index_like_html
```

如果 HTML source 被读取但 parser profile 不存在，或 parser profile 产出 0 个 normalized event：

```text
source_status = html_text_loaded
normalized_event_count = 0
source_format_drift_count += 1
decision = source_audit_failed for that source
schema_quarantine_count is reported
```

支持 source profile：

```text
generic_json_announcement_rows
binance_official_announcements_like_rows
binance_announcement_index_like_html
okx_official_announcements_like_rows
okx_announcement_index_like_html
unlock_calendar_like_rows
```

时间戳规则必须按 source type 区分：

```text
exchange official announcement:
  available_at_ms = source_published_at_ms + EXTERNAL_SIGNAL_STAGE1_5A_PRIMARY_ANNOUNCEMENT_DELAY_MS
  source_timestamp_quality in [official_api_published_at, html_page_time] -> high/medium
  inferred_from_url / missing -> observation_only

unlock calendar with historical snapshot:
  available_at_ms = snapshot_collected_at_ms

unlock calendar without historical snapshot:
  observation_only = true
  hindsight_risk = true
  replay_allowed = false
```

如果同一事件同时存在 API timestamp 与 HTML page timestamp，且二者不一致：

```text
timestamp_source_disagreement_count += 1
timestamp_source_disagreement = true
```

Event type eligibility 按 Filter Matrix 固定，不得事后新增可交易事件类型。

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py -q
git status --short
```

---

## 8. Task 6: Source Audit Summary

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5a_source_audit_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_summary_contains_required_top_level_safety_flags
test_summary_counts_source_resource_safety_fields
test_summary_decision_passed_when_gates_pass
test_source_decision_is_per_source_not_only_global
test_event_type_decision_marks_new_coin_listing_observation_only
test_event_type_decision_marks_whale_deposit_observation_only
test_summary_sparse_inconclusive_when_event_density_low
test_summary_failed_when_available_at_policy_missing
test_summary_failed_when_symbol_mapping_ambiguous_replay_rows_exist
test_summary_failed_when_html_source_yields_zero_normalized_events
test_summary_fixture_run_marks_research_result_valid_false
```

### Step 2: 实现 summary builder

Summary 必须输出：

```text
historical_events_found
overall_decision
source_decisions
event_type_decisions
source_integrity_pass_rate
base_asset_mapping_pass_rate
trade_pair_mapping_pass_rate
symbol_mapping_required_for_replay
multi_symbol_event_count
available_at_policy_defined
forbidden_payload_count
source_resource_safety_policy_defined
source_domain_allowlist_pass_rate
payload_too_large_count
json_depth_exceeded_count
request_timeout_count
retry_budget_exhausted_count
schema_parse_error_count
schema_quarantine_count
symbol_mapping_ambiguous_count
source_format_drift_count
raw_payload_hash_missing_count
timestamp_source_disagreement_count
timestamp_quality_distribution
available_at_delay_sensitivity_required
primary_event_type_events
unique_event_days
symbols_with_events
normalized_event_count
html_text_loaded_count
```

Per-source decision 结构：

```json
{
  "source_decisions": {
    "binance_official_announcements": {
      "decision": "source_audit_passed|source_audit_sparse_inconclusive|source_audit_failed",
      "recommended_event_types_for_stage1_5b": []
    }
  },
  "event_type_decisions": {
    "exchange_delisting_notice": "source_audit_passed|source_audit_sparse_inconclusive|source_audit_failed|observation_only",
    "major_unlock_event": "observation_only"
  }
}
```

Decision 规则：

```text
source_audit_passed:
  historical_events_found >= 30
  primary_event_type_events >= 20
  unique_event_days >= 20
  symbols_with_events >= 3
  source_integrity_pass_rate >= 95%
  trade_pair_mapping_pass_rate >= 95% for replay rows
  timestamp_quality_high_or_medium_ratio >= 95%
  source_resource_safety_policy_defined = true
  forbidden_payload_count = 0
  symbol_mapping_ambiguous_count = 0 for replay rows

source_audit_sparse_inconclusive:
  source safety gates pass
  but density / event days / symbols insufficient

source_audit_failed:
  source unavailable
  available_at_ms cannot be conservatively built
  connector resource safety cannot be defined
  schema parse / symbol mapping errors are silently ignored
  forbidden payload exists
  html_text_loaded = true and normalized_event_count = 0
  source_format_drift_count > 0 for primary source profile
```

Overall decision:

```text
overall_decision = source_audit_passed
  if at least one source_decision passed with at least one eligible event_type passed

overall_decision = source_audit_sparse_inconclusive
  if source safety gates pass but all candidate source/event_type combinations are sparse

overall_decision = source_audit_failed
  if all sources fail or primary source extraction fails due to format drift / timestamp / safety defects
```

`fixture_run = true` 时：

```text
research_result_valid = false
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py -q
git status --short
```

---

## 9. Task 7: Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5a_historical_event_source_audit.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_runner_writes_summary_from_fixture_jsonl
test_runner_rejects_disallowed_domain_before_fetch
test_runner_supports_source_profile_argument
test_runner_does_not_create_replay_outputs
test_runner_fixture_summary_research_result_valid_false
```

### Step 2: 实现 CLI

参数：

```text
--source-profile generic_json_announcement_rows|binance_official_announcements_like_rows|okx_official_announcements_like_rows|unlock_calendar_like_rows
--source-file PATH_OR_GLOB
--source-url URL
--output-summary PATH
--max-pages INT
--fixture-run
```

`--source-profile` 必须支持：

```text
generic_json_announcement_rows
binance_official_announcements_like_rows
binance_announcement_index_like_html
okx_official_announcements_like_rows
okx_announcement_index_like_html
unlock_calendar_like_rows
```

规则：

```text
必须指定 --source-file 或 --source-url 之一
--source-url 时必须通过 domain allowlist
不允许生成 replay summary
不允许生成 TradeIntent
```

真实联网运行必须输出：

```text
raw_cache_written
raw_cache_path
network_result_not_deterministic
collector_received_at_ms
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py -q
git status --short
```

---

## 10. Task 8: Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5a_historical_event_source_audit.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5a_historical_event_source_audit.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_review_states_source_audit_only_not_replay
test_review_lists_connector_resource_safety_report
test_review_lists_timestamp_quality_distribution
test_review_lists_per_source_and_per_event_type_decisions
test_review_mentions_html_zero_normalized_events_as_format_drift_failure
test_review_marks_unlock_calendar_hindsight_risk_observation_only
test_review_states_no_paper_no_live_no_alpha
test_review_recommends_stage1_5b_only_when_source_audit_passed
```

### Step 2: 实现 review script

输入：

```text
--summary PATH
--output-review PATH
```

Review 必须分段：

```text
结论
Source Integrity
Source Resource Safety
Timestamp / Available-at Quality
Event Type / Magnitude / Symbol Mapping
Per-source Decisions
Per-event-type Decisions
Density / Coverage
Stop Reasons
Allowed Next Action
```

如果 `decision = source_audit_passed`：

```text
next_action = write_stage1_5b_minimal_historical_event_table_implementation_plan
```

但只允许把 `source_decisions` 与 `event_type_decisions` 中同时通过的 source/event_type 组合交给 Stage 1.5B。

如果不是 passed：

```text
next_action = fix_source_audit_or_stop_source
```

禁止写：

```text
alpha pass
paper/live
trade signal
execution-ready
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5a_historical_event_source_audit.py -q
git status --short
```

---

## 11. Task 9: Fixture Smoke Artifact

**Files:**
- Create fixture under `tests/fixtures/external_signal_shadow/stage1_5a/`
- Use existing runner/review scripts

### Step 1: 新增 fixture

创建最小 JSONL fixture：

```text
tests/fixtures/external_signal_shadow/stage1_5a/generic_announcements_fixture.jsonl
```

包含：

```text
1 eligible delisting-like event
1 futures launch-like event
1 new_coin_listing excluded event
1 unlock event observation-only
1 forbidden payload row
1 ambiguous symbol mapping row
```

### Step 2: 跑 runner

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5a_historical_event_source_audit.py \
  --source-profile generic_json_announcement_rows \
  --source-file tests/fixtures/external_signal_shadow/stage1_5a/generic_announcements_fixture.jsonl \
  --output-summary data/external_signal_shadow/stage1_5a/fixture_source_audit_summary.json \
  --fixture-run
```

Expected:

```text
fixture_run = true
research_result_valid = false
decision != source_audit_passed
symbol_mapping_ambiguous_count >= 1
source_decisions is present
event_type_decisions is present
```

### Step 3: 跑 review

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5a_historical_event_source_audit.py \
  --summary data/external_signal_shadow/stage1_5a/fixture_source_audit_summary.json \
  --output-review docs/reviews/2026-06-22-external-signal-shadow-lab-stage1-5a-historical-event-source-audit-fixture-review_CN.md
```

Expected:

```text
review explicitly says fixture result is not valid research result
```

### Step 4: 清理或忽略 fixture artifact

不要提交 fixture-generated `data/...` artifact，除非用户明确要求。

```bash
git status --short
```

---

## 12. Task 10: 全量验证

### Step 1: 跑 Stage 1.5A 测试

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_config.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_safety.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_loader.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5a_historical_event_source_audit.py \
  -q
```

Expected: PASS。

### Step 2: 跑相关外部信号回归测试

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

Expected: PASS 或仅存在与本计划无关的已知失败；若失败，必须记录失败测试和原因。

### Step 3: 格式检查

如果项目当前使用 ruff：

```bash
PYTHONPATH=src:. uv run ruff check src/research/external_signal_shadow scripts/external_signal_shadow tests/research/external_signal_shadow tests/scripts/external_signal_shadow
```

Expected: PASS。

### Step 4: 工作区检查

```bash
git status --short
```

Expected: 只包含本计划相关文件；不得包含真实 source audit 产生的大型 data artifact。

---

## 13. 真实 source audit 运行建议

代码通过 fixture smoke 后，再手动选择真实 source 运行。真实 source audit 必须按 source matrix 执行，不得混成一个全局 source。

```text
Source audit matrix:

1. Binance official announcements
   source_name = binance_official_announcements
   source_profile = binance_announcement_index_like_html or binance_official_announcements_like_rows
   input_mode = source_url or cached fixture
   target_event_types = exchange_delisting_notice / futures_contract_launch / trading_pair_removal / trading_pair_addition_for_existing_liquid_asset
   allowed_decision = source_audit_passed / source_audit_sparse_inconclusive / source_audit_failed
   stage1_5b_allowed_only_if = source_decision passed AND event_type_decision passed

2. OKX official announcements
   source_name = okx_official_announcements
   source_profile = okx_announcement_index_like_html or okx_official_announcements_like_rows
   input_mode = source_url or cached fixture
   target_event_types = exchange_delisting_notice / trading_pair_removal / margin_enablement / major_exchange_status_event
   allowed_decision = source_audit_passed / source_audit_sparse_inconclusive / source_audit_failed
   stage1_5b_allowed_only_if = source_decision passed AND event_type_decision passed

3. DefiLlama unlocks
   source_name = defillama_unlocks
   source_profile = unlock_calendar_like_rows
   input_mode = source_url or cached fixture
   target_event_types = major_unlock_event / large_scheduled_token_emission
   allowed_decision = observation_only / source_audit_failed unless historical_snapshot exists
   stage1_5b_allowed_only_if = false in first version

4. Tokenomist unlocks
   source_name = tokenomist_unlocks
   source_profile = unlock_calendar_like_rows
   input_mode = source_url or cached fixture
   target_event_types = major_unlock_event / large_scheduled_token_emission
   allowed_decision = observation_only / source_audit_failed unless historical_snapshot exists
   stage1_5b_allowed_only_if = false in first version
```

真实联网 source audit 必须输出：

```text
raw_cache_written = true
raw_cache_path
network_result_not_deterministic = true
collector_received_at_ms
source_decisions
event_type_decisions
```

真实运行注意：

```text
不要扩大到全网 event calendars
不要接入 API key
不要使用浏览器登录态 / cookie
不要将 low timestamp quality 事件推进 replay
不要把 unlock calendar 直接推进 directional replay
```

真实运行输出 review 后，才允许决定是否写：

```text
Stage 1.5B Minimal Historical Event Table Implementation Plan
```
