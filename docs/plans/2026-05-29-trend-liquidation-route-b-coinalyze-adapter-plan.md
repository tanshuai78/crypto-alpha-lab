# Trend Liquidation Route-B Coinalyze Adapter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将当前 `Route B` 的第三方历史 liquidation 数据路线从 Coinglass 占位实现切换为 Coinalyze 免费 API 可执行适配器，并把其安全地接入 `liquidation_cascade` 的正式 route summary、历史 join 与 replay 审计链路。

**Architecture:** 不修改 live execution，不触碰 `Route A` 的实时 forceOrder 采集链路，只扩展 research / review 层。先把 `scripts/fetch_third_party_liquidation_history.py` 重构为 Coinalyze 驱动的可测试适配器，再新增“按 symbol + hour bucket 输出统一 hourly schema”的落盘与加载流程，最后把 Route B 接入 `scripts/review_trend_liquidation_cascade.py`，让正式审计能基于真实第三方历史 liquidation 数据重跑 `continuation / mean_reversion` 两套 hypothesis。

**Tech Stack:** Python 3.11, pytest, `urllib.request` or existing stdlib HTTP stack, environment variables, JSON, JSONL, existing `scripts/review_trend_liquidation_cascade.py`, existing `src/research/trend_liquidation_cascade_review.py`, Coinalyze REST API, reports under `reports/trend_regime/`, optional output under `data/`.

---

## 1. 决策边界

本计划只解决 4 个问题：

1. 是否能用 **Coinalyze 免费 API** 真实打通 `Route B`
2. 如何把 Coinalyze 的返回字段稳定映射到我们现有的 hourly liquidation schema
3. 如何让正式 `review_trend_liquidation_cascade.py` 使用 Route B 数据重跑历史 replay
4. 如何在 Route B 可用后，重新评估 `Route C` 是否成立

本计划明确不做：

- 不修改 `src/execution/`
- 不修改 `Route A` 的 live forceOrder 容器或服务器采集流程
- 不引入 Coinalyze 数据到 live daemon
- 不提交第三方 raw payload 到 git
- 不提前承诺 Route B 一定能让策略通过，只负责把数据路线接通

本计划必须坚持：

- API key 只能通过环境变量 `COINALYZE_API_KEY` 读取
- pytest 期间禁止真实网络请求
- 第三方数据必须经过统一 adapter，输出与 Route A 一致的 hourly schema
- 正式 reports 只提交聚合 summary，不提交 raw payload 或逐条结果数组
- Coinalyze 请求参数 `from / to` 必须按 **seconds** 发送，系统内部统一使用 **milliseconds**
- Coinalyze 请求必须固定 `convert_to_usd=true`
- Route C `available` 不能只看 Route A / B 同时存在，必须看 `symbol + hour_bucket` overlap

---

## 2. 当前已知前提

1. `liquidation_cascade` 的独立 classifier / replay / review 框架已经存在。
2. 当前 Route B 仍是 Coinglass 占位实现：
   - `scripts/fetch_third_party_liquidation_history.py`
   - `scripts/review_trend_liquidation_cascade.py`
3. 当前正式 review 结论仍是 `continue_data_route_upgrade`，主因不是阈值，而是历史 liquidation 数据覆盖缺失。
4. Coinalyze 官方文档显示：
   - 有 `GET /v1/liquidation-history`
   - 免费 key 限制约 `40 requests/min`
   - `1h` granularity 历史深度约 `1500-2000` points
5. 当前目标 symbols:
   - `BTC/USDT`
   - `ETH/USDT`
   - `SOL/USDT`
   - `XRP/USDT`
   - `DOGE/USDT`

---

## 3. 目标输出

本轮执行完成后，必须至少产出以下 artifact：

1. `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json`
2. `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json`
3. `reports/trend_regime/2026-05-29_liquidation_cascade_data_source_comparison.json`
4. `reports/trend_regime/2026-05-29_liquidation_cascade_viability_summary.json`
5. `reports/trend_regime/2026-05-29_liquidation_cascade_sensitivity.json`
6. `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md`

这些 artifact 必须回答：

- Coinalyze 是否已真实可用
- Route B 的 hourly history 覆盖多少小时、多少 symbol、哪几个 symbol 有缺口
- Route B 接入后 `liquidation_rows_joined_count` 是否从 0 提升
- `continuation / mean_reversion` 是否开始出现非零事件
- Route C 是否从“理论上成立”升级为“工程上可成立”
- Route B 当前属于哪种明确状态：
  - `no_api_key`
  - `api_auth_failed`
  - `api_rate_limited`
  - `api_ok_empty_rows`
  - `api_ok_non_empty_rows`

---

## 4. Files

- Modify: `scripts/fetch_third_party_liquidation_history.py`
- Modify: `scripts/review_trend_liquidation_cascade.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py`
- Modify: `tests/scripts/test_review_trend_liquidation_cascade.py`
- Create: `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_data_source_comparison.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_viability_summary.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_sensitivity.json`

**Commit boundary rules:**
- 只提交代码、测试、review、reports 聚合 summary
- 不提交 `data/*.jsonl`
- 不提交第三方 raw payload
- 不提交大体量 `results` arrays

---

### Task 1: Replace Coinglass Placeholder With Coinalyze Feasibility + Adapter Contract

**Files:**
- Modify: `scripts/fetch_third_party_liquidation_history.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Step 1: Write failing tests for Coinalyze feasibility and normalization**

Add tests for:

```python
def test_load_feasibility_audit_reports_coinalyze_candidate():
    ...


def test_missing_coinalyze_api_key_degrades_gracefully():
    ...


def test_fetch_uses_seconds_timestamps_and_convert_to_usd_true():
    ...


def test_normalize_coinalyze_payload_maps_l_and_s_to_hourly_schema():
    ...


def test_normalize_converts_vendor_t_seconds_to_hour_bucket_ms():
    ...


def test_normalize_handles_empty_history_as_zero_rows():
    ...


def test_normalize_deduplicates_same_symbol_hour_by_sum():
    ...


def test_symbol_to_coinalyze_contract_maps_watchlist_symbols_with_audited_source():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: FAIL because implementation still uses Coinglass assumptions.

**Step 3: Implement Coinalyze route-B adapter**

Refactor `scripts/fetch_third_party_liquidation_history.py`:

- Replace `COINGLASS_API_KEY` with `COINALYZE_API_KEY`
- Add:

```python
def symbol_to_coinalyze_contract(symbol: str) -> str:
    ...


def load_feasibility_audit() -> dict[str, Any]:
    ...


def fetch_historical_liquidations(
    symbol: str,
    *,
    interval: str,
    from_ts_sec: int,
    to_ts_sec: int,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    ...


def normalize_coinalyze_payload(payload: list[dict[str, Any]], *, symbol: str) -> list[dict[str, Any]]:
    ...


def normalize_interval(interval: str) -> str:
    ...
```

Requirements:

- `symbol_to_coinalyze_contract("BTC/USDT")` 允许静态 fallback，但必须输出映射审计信息：

```json
{
  "input_symbol": "BTC/USDT",
  "coinalyze_symbol": "BTCUSDT_PERP.A",
  "exchange": "binance",
  "symbol_on_exchange": "BTCUSDT",
  "base_asset": "BTC",
  "quote_asset": "USDT",
  "is_perpetual": true,
  "margined": "STABLE",
  "mapping_source": "supported_future_markets|static_fallback"
}
```

- `load_feasibility_audit()` must emit:
  - `vendor = coinalyze`
  - `requires_paid_plan = false` or equivalent free-tier semantics
  - `vendor_granularity = 1hour`
  - `normalized_granularity = 1h`
  - `historical_depth_days` based on documented 1500-2000 points at `1h`
  - `route_b_status`
- `fetch_historical_liquidations(...)` must:
  - read `COINALYZE_API_KEY` from env if not explicitly passed
  - return `[]` with warning if key missing
  - remain mock-friendly for tests
  - send `from / to` in **seconds**
  - always send `convert_to_usd=true`
- `normalize_interval("1h") == "1hour"`
- `normalize_interval("1hour") == "1hour"`
- `normalize_coinalyze_payload(...)` must output:
  - `symbol`
  - `vendor_symbol`
  - `hour_bucket_ms`
  - `long_liquidation_notional_1h_usdt`
  - `short_liquidation_notional_1h_usdt`
  - `total_liquidation_notional_1h_usdt`
  - `liquidation_source = third_party_historical`
  - `liquidation_source_quality = historical_vendor_dataset`
  - `vendor_name = coinalyze`
  - `vendor_granularity = 1hour`
  - `normalized_granularity = 1h`
  - `convert_to_usd = true`
  - `timestamp_unit_source = seconds`
- Duplicate `symbol + hour_bucket_ms` rows must be deduplicated by **sum**
- Zero liquidation hours are valid rows; missing rows mean coverage gap

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/fetch_third_party_liquidation_history.py tests/scripts/test_fetch_third_party_liquidation_history.py
git commit -m "feat: switch route-b adapter to coinalyze"
```

---

### Task 2: Add Route-B Hourly Fetch CLI And Summary

**Files:**
- Modify: `scripts/fetch_third_party_liquidation_history.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Step 1: Write failing tests for batch fetch + summary**

Add tests for:

```python
def test_build_route_b_hourly_summary_reports_symbol_and_time_coverage():
    ...


def test_route_b_fetch_cli_aggregates_multiple_symbols_without_network_in_tests():
    ...


def test_build_route_b_hourly_summary_reports_route_b_status():
    ...
```

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: FAIL on missing CLI/summary helpers.

**Step 3: Implement batch hourly exporter**

Add helpers:

```python
def build_route_b_hourly_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ...


def main(argv: list[str] | None = None) -> int:
    ...
```

CLI should support:

```bash
PYTHONPATH=src uv run python scripts/fetch_third_party_liquidation_history.py \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --interval 1hour \
  --lookback-hours 1500 \
  --output-jsonl data/trend_regime_liquidation_hourly_third_party.jsonl \
  --summary-output reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json \
  --feasibility-output reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json
```

Summary must include:

```json
{
  "vendor": "coinalyze",
  "route_b_status": "no_api_key|api_auth_failed|api_rate_limited|api_ok_empty_rows|api_ok_non_empty_rows",
  "symbol_count": 5,
  "symbols": [...],
  "row_count": 0,
  "start_timestamp_ms": 0,
  "end_timestamp_ms": 0,
  "time_span_hours": 0,
  "rows_per_symbol": {},
  "coverage_quality": "historical_vendor_dataset",
  "deduplicated_rows_count": 0,
  "convert_to_usd": true,
  "vendor_granularity": "1hour",
  "normalized_granularity": "1h"
}
```

CLI requirements:

- Add request audit fields:
  - `request_count`
  - `requested_symbols`
  - `interval`
  - `from_ts_sec`
  - `to_ts_sec`
- Respect free-tier rate limit with explicit sleep / pacing

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/fetch_third_party_liquidation_history.py tests/scripts/test_fetch_third_party_liquidation_history.py
git commit -m "feat: add coinalyze route-b hourly export cli"
```

---

### Task 3: Wire Route-B Hourly Data Into Official Cascade Review

**Files:**
- Modify: `scripts/review_trend_liquidation_cascade.py`
- Modify: `tests/scripts/test_review_trend_liquidation_cascade.py`

**Step 1: Write failing tests for route-b join and route decision upgrade**

Add tests for:

```python
def test_review_uses_route_b_hourly_history_when_provided():
    ...


def test_data_source_comparison_marks_route_b_available_when_hourly_rows_exist():
    ...


def test_route_c_available_only_when_route_a_and_route_b_overlap_on_symbol_hour():
    ...
```

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: FAIL on missing Route B integration behavior.

**Step 3: Implement Route-B integration in official review**

Extend `scripts/review_trend_liquidation_cascade.py`:

- Add CLI arg:

```python
--third-party-hourly-input
```

- Load third-party hourly rows
- Join them into historical rows using the same hour-bucket semantics as Route A
- Update route summary:
  - Route B `available = true` when joined data actually exists
  - Route C `available = true` only if Route A and Route B overlap on `symbol + hour_bucket`
- Preserve explicit source boundaries in summary:
  - `liquidation_history_source`
  - `liquidation_history_source_quality`
  - `liquidation_rows_joined_count`
  - `route_a_joined_count`
  - `route_b_joined_count`
  - `route_ab_overlap_symbol_hour_count`

Route summary target shape:

```json
{
  "route_a": {
    "available": true,
    "joined_count": 120,
    "source": "binance_forceorder_hourly",
    "quality": "self_collected_realtime_archive"
  },
  "route_b": {
    "available": true,
    "joined_count": 500,
    "source": "coinalyze_liquidation_history",
    "quality": "historical_vendor_dataset",
    "vendor": "coinalyze",
    "route_b_status": "api_ok_non_empty_rows"
  },
  "route_c": {
    "available": true,
    "definition": "route_a_and_route_b_overlap_on_symbol_hour",
    "overlap_symbol_hour_count": 80
  },
  "decision": "route_b_available_replay_positive_continue_shadow"
}
```

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/review_trend_liquidation_cascade.py tests/scripts/test_review_trend_liquidation_cascade.py
git commit -m "feat: wire coinalyze route-b into cascade review"
```

---

### Task 4: Generate New Route-B-Backed Reports

**Files:**
- Create: `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_data_source_comparison.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_viability_summary.json`
- Create: `reports/trend_regime/2026-05-29_liquidation_cascade_sensitivity.json`

**Step 1: Run Route-B fetch exporter**

Run:

```bash
PYTHONPATH=src uv run python scripts/fetch_third_party_liquidation_history.py \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --interval 1hour \
  --lookback-hours 1500 \
  --output-jsonl data/trend_regime_liquidation_hourly_third_party.jsonl \
  --summary-output reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json \
  --feasibility-output reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json
```

Expected:
- non-empty feasibility summary
- possibly non-empty hourly JSONL if API key works

**Step 2: Run official cascade review with Route B**

Run:

```bash
PYTHONPATH=src uv run python scripts/review_trend_liquidation_cascade.py \
  --rows-input data/trend_regime_historical_rows.jsonl \
  --forceorder-hourly-input data/trend_regime_liquidation_hourly.jsonl \
  --third-party-hourly-input data/trend_regime_liquidation_hourly_third_party.jsonl \
  --route-summary-output reports/trend_regime/2026-05-29_liquidation_cascade_data_source_comparison.json \
  --summary-output reports/trend_regime/2026-05-29_liquidation_cascade_viability_summary.json \
  --sensitivity-output reports/trend_regime/2026-05-29_liquidation_cascade_sensitivity.json
```

**Step 3: Write review**

Create `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md` with required sections:

1. `范围声明`
2. `Coinalyze Route B 可行性结果`
3. `历史 hourly 覆盖`
4. `Route A / B / C 路线状态`
5. `continuation / mean_reversion 事件密度`
6. `成本后 replay 结果`
7. `个人投资者视角评价`
8. `下一步路线建议`
9. `最终结论`

Review decision must use explicit enums:

- `route_b_unavailable_no_key`
- `route_b_unavailable_api_error`
- `route_b_available_but_no_overlap`
- `route_b_available_replay_still_negative`
- `route_b_available_replay_positive_continue_shadow`

**Step 4: Placeholder check**

Run:

```bash
rg -n "TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md
```

Expected: no output.

**Step 5: Commit**

```bash
git add \
  docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md \
  reports/trend_regime/2026-05-29_liquidation_cascade_route_b_feasibility.json \
  reports/trend_regime/2026-05-29_liquidation_cascade_route_b_hourly_summary.json \
  reports/trend_regime/2026-05-29_liquidation_cascade_data_source_comparison.json \
  reports/trend_regime/2026-05-29_liquidation_cascade_viability_summary.json \
  reports/trend_regime/2026-05-29_liquidation_cascade_sensitivity.json
git commit -m "docs: add coinalyze-backed route-b liquidation review"
```

---

## 5. 执行顺序建议

按 3 批执行：

### Batch A：Route-B adapter 基础契约

执行：

- Task 1
- Task 2

通过标准：

- Coinalyze feasibility 输出真实落地
- `COINALYZE_API_KEY` 安全降级正常
- hourly schema 与 Route A 对齐
- batch fetch CLI 能生成 summary
- 秒/毫秒转换被测试锁住
- `convert_to_usd=true` 被测试锁住

### Batch B：正式 review 接线

执行：

- Task 3

通过标准：

- Route B hourly history 能进入 `review_trend_liquidation_cascade.py`
- Route summary 能正确显示 Route B / C 可用性
- Route A / B 证据边界仍然清楚
- Route C 只在 overlap 存在时成立

### Batch C：Route-B-backed 审计

执行：

- Task 4

通过标准：

- 正式 reports 生成成功
- review 明确说明 Route B 是否真的打通
- 若 Route B 可用，则正式 replay 不再是 liquidation coverage = 0
- review 决策枚举明确，不再只用模糊 true/false

---

## 6. 完成定义

本计划完成后，必须做到：

- `Route B` 不再是 Coinglass 占位状态，而是 Coinalyze 可执行状态
- 第三方历史 liquidation 数据能以统一 schema 进入 `liquidation_cascade` replay
- 正式 route summary 能区分：
  - Route A only
  - Route B available
  - Route C available
- Route C 只在 symbol-hour overlap 存在时可用
- 可以明确回答：在免费 Coinalyze 路线下，我们是否已经拥有足够历史 liquidation 数据来重新审查 `liquidation_cascade`
